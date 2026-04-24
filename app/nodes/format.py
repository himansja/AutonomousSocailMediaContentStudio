"""
FORMAT node — Output Formatter LLM (additional layer).

This is a dedicated LLM call that takes the approved posts and
transforms them into a clean, structured, publish-ready content package.
It handles final polish: consistent hashtag ordering, emoji placement,
line-break formatting, and a summary cover note.
"""
import json
from app.core.llm import llm
from app.core.logger import logger
from app.state.state import ContentState
from app.prompts.format_prompts import FORMAT_PROMPT


def format_node(state: ContentState) -> ContentState:
    logger.info("[FORMAT] Formatting approved posts into publish-ready output...")
    # Summarise the plan to first 500 chars to keep the prompt tight
    plan_summary = state["content_plan"][:500] + (
        "..." if len(state["content_plan"]) > 500 else ""
    )

    prompt = FORMAT_PROMPT.format(
        posts=json.dumps(state["posts"], indent=2),
        content_plan_summary=plan_summary,
        overall_score=round(state.get("overall_score", 0.0), 1),
        iteration_count=state["iteration_count"],
    )
    response = llm.invoke(prompt)
    raw = response.content.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        json.loads(raw)  # validate it's parseable
        final_output = raw
    except json.JSONDecodeError:
        logger.warning("[FORMAT] LLM returned non-JSON, using raw text fallback")
        posts = state.get("posts", {})
        final_output = json.dumps({
            "linkedin": {"content": posts.get("linkedin", "")},
            "twitter":  {"content": posts.get("x", "")},
            "instagram":{"content": posts.get("instagram", "")},
        })

    logger.info("[FORMAT] Final output ready (%d chars)", len(final_output))
    new_state = dict(state)
    new_state["final_output"] = final_output
    new_state["approval_status"] = True
    new_state["history"] = ["[FORMAT] Final publish-ready package produced."]
    return new_state
