import asyncio
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from app.graph.graph import compiled_graph  # noqa: E402 — after load_dotenv

app = FastAPI(title="Autonomous Social Media Content Studio")


def _render_final_output(posts: dict) -> str:
    sections = [
        "LinkedIn\n--------\n" + posts.get("linkedin", ""),
        "Twitter / X\n-----------\n" + posts.get("x", ""),
        "Instagram\n---------\n" + posts.get("instagram", ""),
    ]
    return "\n\n".join(sections)


# ── Request / Response schemas ────────────────────────────────────────────────

class ContentRequest(BaseModel):
    input_content: str
    max_iterations: int = 3


class ContentResponse(BaseModel):
    final_output: str
    overall_score: float
    iteration_count: int
    posts: dict
    history: list


# ── Endpoint ──────────────────────────────────────────────────────────────────

@app.post("/generate", response_model=ContentResponse)
async def generate_content(request: ContentRequest):
    if not request.input_content.strip():
        raise HTTPException(status_code=400, detail="input_content cannot be empty")

    initial_state = {
        "input_content": request.input_content,
        "content_plan": "",
        "posts": {},
        "feedback": {},
        "overall_score": 0.0,
        "final_output": "",
        "history": [],
        "approval_status": False,
        "iteration_count": 0,
        "max_iterations": request.max_iterations,
    }

    try:
        final_state = await asyncio.to_thread(compiled_graph.invoke, initial_state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ContentResponse(
        final_output=final_state.get("final_output") or _render_final_output(final_state["posts"]),
        overall_score=final_state.get("overall_score", 0.0),
        iteration_count=final_state["iteration_count"],
        posts=final_state["posts"],
        history=final_state["history"],
    )


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

