"""
Parallel Platform Agent Nodes — LinkedIn, X, Instagram.

Each agent runs independently (fanned-out via LangGraph Send API).
They all write into `posts` which uses a merge_dicts reducer, so
parallel writes are safe — no key collision between platforms.

Also exports `platform_fan_out` used by graph.py to dispatch Send messages.
"""
from langgraph.types import Send

from app.core.llm import llm
from app.core.logger import logger
from app.state.state import ContentState


# ── Per-platform system prompts ───────────────────────────────────────────────

LINKEDIN_PROMPT = """You are the LinkedIn Content Agent.

Content strategy plan:
{content_plan}

Original content idea:
{input_content}

{feedback_section}

Write a LinkedIn post:
- 150-300 words
- Professional, thought-leadership tone
- Structured paragraphs
- 3-5 relevant hashtags on a new line at the end
- No emojis in the body; one optional in the opening hook

Return ONLY the post text. No JSON.
"""

X_PROMPT = """You are the X (Twitter) Content Agent.

Content strategy plan:
{content_plan}

Original content idea:
{input_content}

{feedback_section}

Write a single tweet:
- MAX 280 characters (strictly enforced)
- Punchy opening hook
- 1-2 inline hashtags
- Conversational, engaging tone

Return ONLY the tweet text. No JSON.
"""

INSTAGRAM_PROMPT = """You are the Instagram Caption Agent.

Content strategy plan:
{content_plan}

Original content idea:
{input_content}

{feedback_section}

Write an Instagram caption:
- 100-150 words of storytelling body
- Double line break, then 5-10 hashtags grouped at the bottom
- End the body with a clear Call-To-Action
- Warm, visual, community-focused tone

Return ONLY the caption text. No JSON.
"""

PLATFORM_PROMPTS = {
    "linkedin": LINKEDIN_PROMPT,
    "x": X_PROMPT,
    "instagram": INSTAGRAM_PROMPT,
}


# ── Shared helper ─────────────────────────────────────────────────────────────

def _build_feedback_section(state: ContentState, platform: str) -> str:
    feedback = state.get("feedback", {})
    if platform in feedback:
        return f"Previous reviewer feedback for this platform to address:\n{feedback[platform]}"
    return ""


# ── Individual platform agent nodes ──────────────────────────────────────────

def linkedin_agent(state: ContentState) -> ContentState:
    logger.info("[ACT] LinkedIn Agent generating post...")
    prompt = PLATFORM_PROMPTS["linkedin"].format(
        content_plan=state["content_plan"],
        input_content=state["input_content"],
        feedback_section=_build_feedback_section(state, "linkedin"),
    )
    response = llm.invoke(prompt)
    post = response.content.strip()
    logger.debug("[ACT] LinkedIn post (%d chars)", len(post))
    new_state = dict(state)
    new_state["posts"] = {"linkedin": post}
    new_state["history"] = ["[ACT] LinkedIn Agent wrote post."]
    return new_state


def x_agent(state: ContentState) -> ContentState:
    logger.info("[ACT] X (Twitter) Agent generating post...")
    prompt = PLATFORM_PROMPTS["x"].format(
        content_plan=state["content_plan"],
        input_content=state["input_content"],
        feedback_section=_build_feedback_section(state, "x"),
    )
    response = llm.invoke(prompt)
    post = response.content.strip()
    # Enforce 280 char limit
    if len(post) > 280:
        logger.warning("[ACT] X post truncated from %d to 280 chars", len(post))
        post = post[:277] + "..."
    logger.debug("[ACT] X post (%d chars)", len(post))
    new_state = dict(state)
    new_state["posts"] = {"x": post}
    new_state["history"] = ["[ACT] X Agent wrote post."]
    return new_state


def instagram_agent(state: ContentState) -> ContentState:
    logger.info("[ACT] Instagram Agent generating caption...")
    prompt = PLATFORM_PROMPTS["instagram"].format(
        content_plan=state["content_plan"],
        input_content=state["input_content"],
        feedback_section=_build_feedback_section(state, "instagram"),
    )
    response = llm.invoke(prompt)
    post = response.content.strip()
    logger.debug("[ACT] Instagram caption (%d chars)", len(post))
    new_state = dict(state)
    new_state["posts"] = {"instagram": post}
    new_state["history"] = ["[ACT] Instagram Agent wrote caption."]
    return new_state


# ── Fan-out function (called as conditional edge from plan / reflect) ─────────

def platform_fan_out(state: ContentState) -> list[Send]:
    """Dispatch all three platform agents in parallel via LangGraph Send API."""
    return [
        Send("linkedin_agent", state),
        Send("x_agent", state),
        Send("instagram_agent", state),
    ]

