"""
REPLAN node — unified replanner that handles both full and targeted revision.

Logic:
  - ALL platforms failed → full strategy replan (all 3 agents re-run)
  - SOME platforms failed → targeted fix for failing platforms only (passing posts kept)
"""
import re

from app.core.llm import invoke_cached, usage_delta
from app.core.logger import logger
from app.state.state import ContentState
from app.graph.routing import PLATFORM_FAIL_THRESHOLD
from app.prompts.replan_prompts import REPLAN_SYSTEM, REPLAN_HUMAN, TARGETED_REPLAN_SYSTEM, TARGETED_REPLAN_HUMAN


def _parse_score(feedback_str: str) -> float:
    """Extract numeric score from 'Score X/10 | ...' string."""
    match = re.match(r"Score (\d+(?:\.\d+)?)/10", feedback_str)
    return float(match.group(1)) if match else 5.0


def replan_node(state: ContentState) -> ContentState:
    """
    Unified replanner:
      - If ALL platforms failed → full replan (broad strategy revision, all agents retry)
      - If only SOME platforms failed → targeted fix (only failing agents retry, passing posts kept)
    """
    feedback = state.get("feedback", {})

    failing = {
        platform: fb
        for platform, fb in feedback.items()
        if _parse_score(fb) < PLATFORM_FAIL_THRESHOLD
    }

    # Fallback: nothing below threshold but we're still replanning → retry the worst one
    if not failing and feedback:
        worst = min(feedback.items(), key=lambda kv: _parse_score(kv[1]))
        failing = {worst[0]: worst[1]}
        logger.debug(
            "[REPLAN] No platform below fail threshold (%.1f); retrying lowest scorer: %s (%.1f)",
            PLATFORM_FAIL_THRESHOLD, worst[0], _parse_score(worst[1]),
        )

    all_failed = len(failing) == len(feedback)  # True → full replan; False → targeted fix
    platforms_to_retry = [] if all_failed else list(failing.keys())

    if all_failed:
        logger.info("[REPLAN] All platforms failed — full strategy replan (iteration %d)",
                    state["iteration_count"])
        response = invoke_cached(
            system_text=REPLAN_SYSTEM,
            human_text=REPLAN_HUMAN.format(
                input_content=state["input_content"],
                content_plan=state.get("content_plan", ""),
                feedback=feedback,
            ),
            logger=logger,
        )
    else:
        logger.info("[REPLAN] Targeted fix for %s (iteration %d)",
                    list(failing.keys()), state["iteration_count"])
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

    revised_plan = str(response.content).strip()
    logger.debug("[REPLAN] Revised plan (%d chars)", len(revised_plan))

    new_state = dict(state)
    new_state["token_usage"] = usage_delta(response)
    new_state["content_plan"] = revised_plan
    new_state["platforms_to_retry"] = platforms_to_retry
    new_state["history"] = [
        f"[REPLAN] {'Full' if all_failed else 'Targeted'} replan after iteration "
        f"{state['iteration_count']} — retrying: {'all' if all_failed else platforms_to_retry}."
    ]
    return new_state
