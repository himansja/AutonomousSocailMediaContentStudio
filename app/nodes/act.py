"""
Parallel Platform Agent Nodes — LinkedIn, X, Instagram.

Each agent runs independently (fanned-out via LangGraph Send API).
They all write into `posts` which uses a merge_dicts reducer, so
parallel writes are safe — no key collision between platforms.

Also exports `platform_fan_out` used by graph.py to dispatch Send messages.
"""
from langgraph.types import Send

from app.core.llm import invoke_cached, usage_delta
from app.core.logger import logger
from app.state.state import ContentState
from app.prompts.act_prompts import PLATFORM_SYSTEMS, PLATFORM_HUMAN
from app.tools.character_counter import character_counter


# ── Shared helper ─────────────────────────────────────────────────────────────

def _build_feedback_section(state: ContentState, platform: str) -> str:
    feedback = state.get("feedback", {})
    if platform in feedback:
        return f"Previous reviewer feedback for this platform to address:\n{feedback[platform]}"
    return ""


# ── Individual platform agent nodes ──────────────────────────────────────────

def linkedin_agent(state: ContentState) -> ContentState:
    logger.info("[ACT] LinkedIn Agent generating post...")
    response = invoke_cached(
        system_text=PLATFORM_SYSTEMS["linkedin"],
        human_text=PLATFORM_HUMAN.format(
            content_plan=state["content_plan"],
            input_content=state["input_content"],
            feedback_section=_build_feedback_section(state, "linkedin"),
        ),
        logger=logger,
    )
    post = str(response.content).strip()
    logger.debug("[ACT] LinkedIn post (%d chars)", len(post))
    return {"posts": {"linkedin": post}, "token_usage": usage_delta(response), "history": ["[ACT] LinkedIn Agent wrote post."]}  # type: ignore[return-value]


def x_agent(state: ContentState) -> ContentState:
    logger.info("[ACT] X (Twitter) Agent generating post...")
    response = invoke_cached(
        system_text=PLATFORM_SYSTEMS["x"],
        human_text=PLATFORM_HUMAN.format(
            content_plan=state["content_plan"],
            input_content=state["input_content"],
            feedback_section=_build_feedback_section(state, "x"),
        ),
        logger=logger,
    )
    post = str(response.content).strip()
    result = character_counter.invoke({"text": post})
    if result["trimmed"]:
        logger.warning("[ACT] X post trimmed from %d to %d chars",
                       result["char_count"], result["limit"])
    post = result["text"]
    logger.debug("[ACT] X post (%d chars)", len(post))
    return {"posts": {"x": post}, "token_usage": usage_delta(response), "history": ["[ACT] X Agent wrote post."]}  # type: ignore[return-value]


def instagram_agent(state: ContentState) -> ContentState:
    logger.info("[ACT] Instagram Agent generating caption...")
    response = invoke_cached(
        system_text=PLATFORM_SYSTEMS["instagram"],
        human_text=PLATFORM_HUMAN.format(
            content_plan=state["content_plan"],
            input_content=state["input_content"],
            feedback_section=_build_feedback_section(state, "instagram"),
        ),
        logger=logger,
    )
    post = str(response.content).strip()
    logger.debug("[ACT] Instagram caption (%d chars)", len(post))
    return {"posts": {"instagram": post}, "token_usage": usage_delta(response), "history": ["[ACT] Instagram Agent wrote caption."]}  # type: ignore[return-value]


# ── Fan-out function (called as conditional edge from plan / reflect) ─────────

def platform_fan_out(state: ContentState) -> list[Send]:
    """
    Dispatch platform agents in parallel via LangGraph Send API.
    - Initial run (platforms_to_retry is empty): dispatch all three.
    - Retry run: dispatch ONLY platforms that failed review.
    """
    platforms_to_retry: list = state.get("platforms_to_retry", [])

    platform_map = {
        "linkedin":  "linkedin_agent",
        "x":         "x_agent",
        "instagram": "instagram_agent",
    }

    if platforms_to_retry:
        targets = [platform_map[p] for p in platforms_to_retry if p in platform_map]
        logger.info("[FAN-OUT] Selective retry for failed platforms: %s", platforms_to_retry)
    else:
        targets = list(platform_map.values())
        logger.info("[FAN-OUT] Initial run — dispatching all three platform agents")

    return [Send(node, state) for node in targets]

