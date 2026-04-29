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

from app.core.llm import invoke_cached, usage_delta
from app.core.logger import logger
from app.state.state import ContentState
from app.graph.routing import QUALITY_THRESHOLD, PLATFORM_FAIL_THRESHOLD
from app.prompts.replan_prompts import TARGETED_REPLAN_SYSTEM, TARGETED_REPLAN_HUMAN


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
        if _parse_score(fb) < PLATFORM_FAIL_THRESHOLD
    }

    # If no platform is genuinely failing but we still got here, pick the
    # lowest-scoring one so the loop always makes progress.
    if not failing and feedback:
        worst = min(feedback.items(), key=lambda kv: _parse_score(kv[1]))
        failing = {worst[0]: worst[1]}
        logger.debug(
            "[REFLECT] No platform below fail threshold (%.1f); retrying lowest scorer: %s (%.1f)",
            PLATFORM_FAIL_THRESHOLD, worst[0], _parse_score(worst[1]),
        )

    platforms_to_retry = list(failing.keys())
    logger.info("[REFLECT] Failed platforms: %s (iteration %d)",
                platforms_to_retry, state["iteration_count"])

    failing_feedback_str = "\n".join(
        f"- {p.upper()}: {fb}" for p, fb in failing.items()
    )

    response = invoke_cached(
        system_text=TARGETED_REPLAN_SYSTEM,
        human_text=TARGETED_REPLAN_HUMAN.format(
            input_content=state["input_content"],
            content_plan=state.get("content_plan", ""),
            failing_feedback=failing_feedback_str,
        ),
        logger=logger,
    )
    revised_plan = response.content.strip()
    logger.debug("[REFLECT] Revised plan (%d chars)", len(revised_plan))

    new_state = dict(state)
    new_state["token_usage"] = usage_delta(response)
    new_state["content_plan"] = revised_plan
    new_state["platforms_to_retry"] = platforms_to_retry
    new_state["history"] = [
        f"[REFLECT] Replanning for {platforms_to_retry} after iteration {state['iteration_count']}."
    ]
    return new_state

