"""
PLAN and REPLAN nodes for the Content Manager.

`plan_node` creates the initial strategy from the raw idea.
`replan_node` revises that strategy after review feedback and sends the
workflow back through the parallel platform agents.
"""
from app.core.llm import invoke_cached, usage_delta
from app.core.logger import logger
from app.state.state import ContentState
from app.prompts.plan_prompts import PLAN_SYSTEM, PLAN_HUMAN
from app.tools.web_search import web_search
from app.tools.read_file_tool import read_uploaded_file
from app.tools.read_url_tool import read_url


def _format_search_results(results: list[dict]) -> str:
    if not results:
        return "No search results found."
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['title']}\n   {r['snippet']}\n   Source: {r['url']}")
    return "\n\n".join(lines)


def _load_source_content(state: ContentState) -> str:
    """
    Returns the primary source content (from uploaded file or URL) as a string,
    or an empty string when neither is provided.
    """
    uploaded_path = state.get("uploaded_file_path", "")
    source_url = state.get("source_url", "")

    _ERROR_PREFIXES = ("file not found:", "error reading", "unsupported file type", "pdf support requires", "no readable text", "invalid url:", "error fetching")

    def _is_error(text: str) -> bool:
        return text.lower().startswith(_ERROR_PREFIXES)

    if uploaded_path:
        logger.info("[PLAN] Reading uploaded file: %s", uploaded_path)
        try:
            content = read_uploaded_file.invoke(
                {"file_path": uploaded_path, "max_chars": 8000}
            )
            if _is_error(content):
                logger.warning("[PLAN] File read returned an error: %s", content)
                return ""
            logger.debug("[PLAN] File read: %d chars", len(content))
            return content
        except Exception as exc:
            logger.warning("[PLAN] Failed to read uploaded file (%s)", exc)
            return ""

    if source_url:
        logger.info("[PLAN] Fetching source URL: %s", source_url)
        try:
            content = read_url.invoke({"url": source_url, "max_chars": 8000})
            if _is_error(content):
                logger.warning("[PLAN] URL fetch returned an error: %s", content)
                return ""
            logger.debug("[PLAN] URL fetched: %d chars", len(content))
            return content
        except Exception as exc:
            logger.warning("[PLAN] Failed to fetch source URL (%s)", exc)
            return ""

    return ""


def plan_node(state: ContentState) -> ContentState:
    input_content = state["input_content"]

    # ── Optional: load primary source content (file or URL) ──────────────────
    source_content = _load_source_content(state)
    if source_content:
        source_content_section = (
            "PRIMARY SOURCE CONTENT (blog post / article supplied by the user — "
            "treat this as the main material to base the content on):\n"
            f"{source_content}\n\n"
        )
        history_note = "[PLAN] Source content loaded. Web research complete. Initial content strategy created."
    else:
        source_content_section = ""
        history_note = "[PLAN] Web research complete. Initial content strategy created."

    # If no explicit topic was given, derive a search query from the source material
    search_query = input_content or state.get("source_url", "") or source_content[:200]

    # ── Search 1: background facts about the topic ────────────────────────────
    logger.info("[PLAN] Searching for background research on topic...")
    try:
        topic_results = web_search.invoke({"query": search_query, "max_results": 5})
        topic_context = _format_search_results(topic_results)
        logger.debug("[PLAN] Topic search returned %d results", len(topic_results))
    except Exception as e:
        logger.warning("[PLAN] Topic search failed (%s)", str(e))
        topic_context = "No topic research available."

    # ── Search 2: what's trending on social media around this topic ───────────
    logger.info("[PLAN] Searching for trending social media content on topic...")
    try:
        trend_query = f"trending social media content {search_query} 2026"
        trend_results = web_search.invoke({"query": trend_query, "max_results": 5})
        trend_context = _format_search_results(trend_results)
        logger.debug("[PLAN] Trend search returned %d results", len(trend_results))
    except Exception as e:
        logger.warning("[PLAN] Trend search failed (%s)", str(e))
        trend_context = "No trend data available."

    search_context = f"TOPIC RESEARCH:\n{topic_context}\n\nTRENDING CONTENT:\n{trend_context}"

    logger.info("[PLAN] Building initial content strategy...")
    response = invoke_cached(
        system_text=PLAN_SYSTEM,
        human_text=PLAN_HUMAN.format(
            input_content=input_content or "(derived from source content above)",
            source_content_section=source_content_section,
            search_context=search_context,
        ),
        logger=logger,
    )
    content_plan = str(response.content).strip()

    new_state = dict(state)
    new_state["content_plan"] = content_plan
    new_state["search_results"] = search_context
    new_state["posts"] = {}
    new_state["feedback"] = {}
    new_state["overall_score"] = 0.0
    new_state["final_output"] = ""
    new_state["iteration_count"] = 0
    new_state["approval_status"] = False
    new_state["platforms_to_retry"] = []
    new_state["history"] = [history_note]
    return new_state
