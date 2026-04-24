import asyncio
import uvicorn
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

load_dotenv()

import json as _json  # noqa: E402

from app.graph.graph import compiled_graph  # noqa: E402 — after load_dotenv
from app.models.models import ContentRequest, ContentResponse, PlatformContent, MetaInfo  # noqa: E402
from app.core.logger import logger  # noqa: E402

app = FastAPI(title="Autonomous Social Media Content Studio")


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
        ),
    )


# ── Endpoint ──────────────────────────────────────────────────────────────────

@app.post("/generate", response_model=ContentResponse)
async def generate_content(request: ContentRequest):
    if not request.input_content.strip():
        raise HTTPException(status_code=400, detail="input_content cannot be empty")

    logger.info("POST /generate | max_iterations=%d | content_length=%d",
                request.max_iterations, len(request.input_content))

    initial_state = {
        "input_content": request.input_content,
        "content_plan": "",
        "search_results": "",
        "posts": {},
        "feedback": {},
        "overall_score": 0.0,
        "final_output": "",
        "history": [],
        "approval_status": False,
        "iteration_count": 0,
        "max_iterations": request.max_iterations,
        "platforms_to_retry": [],
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

