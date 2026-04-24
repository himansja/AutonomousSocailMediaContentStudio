"""
REFLECT node — Targeted replan for failed platforms only.

In the Plan-Act-Check loop:
  PLAN  → create initial strategy
  ACT   → parallel platform agents generate posts
  CHECK → reviewer scores each platform
  REFLECT → identifies ONLY failing platforms, revises plan for them,
             and sets platforms_to_retry so the fan-out dispatches only
             the agents that need to redo their work.
"""
import re

from app.core.llm import llm
from app.core.logger import logger
from app.state.state import ContentState
from app.graph.routing import QUALITY_THRESHOLD
from app.prompts.replan_prompts import TARGETED_REPLAN_PROMPT


def _parse_score(feedback_str: str) -> float:
    """Extract numeric score from 'Score X/10 | ...' string."""
    match = re.match(r"Score (\d+(?:\.\d+)?)/10", feedback_str)
    return float(match.group(1)) if match else 5.0


def reflect_node(state: ContentState) -> ContentState:
    """
    Identify which platforms failed (score < QUALITY_THRESHOLD),
    update the content plan with targeted fixes for those platforms only,
    and record platforms_to_retry so platform_fan_out skips passing platforms.
    """
    feedback = state.get("feedback", {})

    failing = {
        platform: fb
        for platform, fb in feedback.items()
        if _parse_score(fb) < QUALITY_THRESHOLD
    }

    platforms_to_retry = list(failing.keys())
    logger.info("[REFLECT] Failed platforms: %s (iteration %d)",
                platforms_to_retry, state["iteration_count"])

    failing_feedback_str = "\n".join(
        f"- {p.upper()}: {fb}" for p, fb in failing.items()
    )

    prompt = TARGETED_REPLAN_PROMPT.format(
        input_content=state["input_content"],
        content_plan=state.get("content_plan", ""),
        failing_feedback=failing_feedback_str,
    )
    response = llm.invoke(prompt)
    revised_plan = response.content.strip()
    logger.debug("[REFLECT] Revised plan (%d chars)", len(revised_plan))

    new_state = dict(state)
    new_state["content_plan"] = revised_plan
    new_state["platforms_to_retry"] = platforms_to_retry
    new_state["history"] = [
        f"[REFLECT] Replanning for {platforms_to_retry} after iteration {state['iteration_count']}."
    ]
    return new_state

