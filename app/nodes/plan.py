"""
PLAN and REPLAN nodes for the Content Manager.

`plan_node` creates the initial strategy from the raw idea.
`replan_node` revises that strategy after review feedback and sends the
workflow back through the parallel platform agents.
"""
from app.core.llm import llm
from app.core.logger import logger
from app.state.state import ContentState
from app.prompts.plan_prompts import PLAN_PROMPT, REPLAN_PROMPT
from app.tools.web_search import web_search


def _format_search_results(results: list[dict]) -> str:
    if not results:
        return "No search results found."
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['title']}\n   {r['snippet']}\n   Source: {r['url']}")
    return "\n\n".join(lines)


def plan_node(state: ContentState) -> ContentState:
    logger.info("[PLAN] Searching for background research on topic...")
    try:
        results = web_search.invoke({"query": state["input_content"], "max_results": 5})
        search_context = _format_search_results(results)
        logger.debug("[PLAN] Search returned %d results", len(results))
    except Exception as e:
        logger.warning("[PLAN] Web search failed (%s) — proceeding without research", str(e))
        search_context = "No search results available."

    logger.info("[PLAN] Building initial content strategy...")
    prompt = PLAN_PROMPT.format(
        input_content=state["input_content"],
        search_context=search_context,
    )
    response = llm.invoke(prompt)
    content_plan = response.content.strip()
    logger.debug("[PLAN] Strategy created (%d chars)", len(content_plan))

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
    new_state["history"] = ["[PLAN] Web research complete. Initial content strategy created."]
    return new_state


def replan_node(state: ContentState) -> ContentState:
    logger.info("[REPLAN] Revising strategy after iteration %d (score=%.1f)...",
                state["iteration_count"], state.get("overall_score", 0.0))
    prompt = REPLAN_PROMPT.format(
        input_content=state["input_content"],
        content_plan=state.get("content_plan", ""),
        feedback=state.get("feedback", {}),
    )
    response = llm.invoke(prompt)
    revised_plan = response.content.strip()
    logger.debug("[REPLAN] Revised strategy (%d chars)", len(revised_plan))

    new_state = dict(state)
    new_state["content_plan"] = revised_plan
    new_state["final_output"] = ""
    new_state["history"] = [
        f"[REPLAN] Strategy revised after review iteration {state['iteration_count']}."
    ]
    return new_state
