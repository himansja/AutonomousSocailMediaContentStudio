import asyncio
import secrets
import shutil
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File
from dotenv import load_dotenv

load_dotenv()

import json as _json  # noqa: E402

from app.graph.graph import compiled_graph  # noqa: E402 — after load_dotenv
from app.models.models import ContentRequest, ContentResponse, PlatformContent, MetaInfo, TokenUsage  # noqa: E402
from app.core.logger import logger  # noqa: E402

app = FastAPI(title="Autonomous Social Media Content Studio")

# Directory where uploaded files are stored; created on startup if absent
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

_ALLOWED_EXTENSIONS = {".txt", ".md", ".rst", ".csv", ".pdf"}


def _build_response(final_state: dict) -> ContentResponse:
    """Parse the JSON final_output from the format node into the typed response."""
    posts = final_state.get("posts", {})
    formatted: dict = {}

    raw = final_state.get("final_output", "")
    if raw:
        try:
            formatted = _json.loads(raw)
        except _json.JSONDecodeError:
            logger.warning("Could not parse final_output JSON; falling back to raw posts")

    return ContentResponse(
        linkedin=PlatformContent(
            content=formatted.get("linkedin", {}).get("content", posts.get("linkedin", ""))
        ),
        twitter=PlatformContent(
            content=formatted.get("twitter", {}).get("content", posts.get("x", ""))
        ),
        instagram=PlatformContent(
            content=formatted.get("instagram", {}).get("content", posts.get("instagram", ""))
        ),
        meta=MetaInfo(
            iterations=final_state["iteration_count"],
            overall_score=final_state.get("overall_score", 0.0),
            approved=final_state.get("approval_status", False),
            token_usage=TokenUsage(**final_state.get("token_usage", {})),
        ),
    )


# ── Upload endpoint ───────────────────────────────────────────────────────────

@app.post("/upload", summary="Upload a source file (blog post, article, etc.)")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a text/document file to use as primary source material for content generation.

    Supported types: .txt, .md, .rst, .csv, .pdf

    Returns:
        `file_path` — pass this value as `uploaded_file_path` in the `/generate` request body.
    """
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: {sorted(_ALLOWED_EXTENSIONS)}",
        )

    # Use a random token to avoid collisions and prevent path traversal
    safe_name = f"{secrets.token_hex(16)}{suffix}"
    dest = UPLOAD_DIR / safe_name

    try:
        with dest.open("wb") as out:
            shutil.copyfileobj(file.file, out)
    finally:
        await file.close()

    logger.info("File uploaded: %s (%s)", safe_name, file.filename)
    return {"file_path": str(dest), "original_filename": file.filename}


# ── Generate endpoint ─────────────────────────────────────────────────────────

@app.post("/generate", response_model=ContentResponse)
async def generate_content(request: ContentRequest):
    # Validate uploaded_file_path when provided
    if request.uploaded_file_path:
        fp = Path(request.uploaded_file_path)
        if not fp.exists() or not fp.is_file():
            raise HTTPException(
                status_code=400,
                detail=f"uploaded_file_path not found: {request.uploaded_file_path}",
            )

    logger.info(
        "POST /generate | max_iterations=%d | content_length=%d | source_url=%s | has_file=%s",
        request.max_iterations,
        len(request.input_content or ""),
        bool(request.source_url),
        bool(request.uploaded_file_path),
    )

    initial_state = {
        "input_content": request.input_content or "",
        "source_url": request.source_url or "",
        "uploaded_file_path": request.uploaded_file_path or "",
        "content_plan": "",
        "search_results": "",
        "posts": {},
        "feedback": {},
        "overall_score": 0.0,
        "previous_score": 0.0,
        "final_output": "",
        "history": [],
        "approval_status": False,
        "iteration_count": 0,
        "max_iterations": request.max_iterations,
        "platforms_to_retry": [],
        "token_usage": {
            "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
            "cached_tokens": 0, "cache_hits": 0, "cache_misses": 0,
        },
    }

    try:
        final_state = await asyncio.to_thread(compiled_graph.invoke, initial_state)
    except Exception as e:
        logger.error("Graph execution failed: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    logger.info("Workflow complete | iterations=%d | score=%.1f | approved=%s",
                final_state["iteration_count"],
                final_state.get("overall_score", 0.0),
                final_state.get("approval_status", False))

    return _build_response(final_state)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

