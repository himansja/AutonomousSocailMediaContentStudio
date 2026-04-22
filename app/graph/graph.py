"""
LangGraph workflow: Autonomous Social Media Content Studio

Architecture:
  START
    ↓
  Manager Plan
    ↓
  FAN-OUT to LinkedIn / Twitter / Instagram agents
    ↓
  FAN-IN to Review
    ↓
  [Approved?]
    ├── Yes → END
    └── No  → Replan → FAN-OUT again
"""
from langgraph.graph import StateGraph, START, END

from app.state.state import ContentState
from app.nodes.plan import plan_node, replan_node
from app.nodes.act import linkedin_agent, x_agent, instagram_agent, platform_fan_out
from app.nodes.check import check_node
from app.graph.routing import should_continue


def build_graph() -> StateGraph:
    graph = StateGraph(ContentState)

    # ── Register nodes ────────────────────────────────────────────────────────
    graph.add_node("plan", plan_node)
    graph.add_node("replan", replan_node)
    graph.add_node("linkedin_agent", linkedin_agent)
    graph.add_node("x_agent", x_agent)
    graph.add_node("instagram_agent", instagram_agent)
    graph.add_node("review", check_node)

    # ── Entry point ───────────────────────────────────────────────────────────
    graph.add_edge(START, "plan")

    # ── plan fans out to three parallel platform agents ───────────────────────
    graph.add_conditional_edges("plan", platform_fan_out, ["linkedin_agent", "x_agent", "instagram_agent"])

    # ── All three agents converge into review (fan-in) ────────────────────────
    graph.add_edge("linkedin_agent", "review")
    graph.add_edge("x_agent", "review")
    graph.add_edge("instagram_agent", "review")

    # ── Conditional routing after review ─────────────────────────────────────
    graph.add_conditional_edges(
        "review",
        should_continue,
        {
        "approve": END,
        "replan": "replan",
        },
    )

    # ── Replan re-fans out to parallel agents ─────────────────────────────────
    graph.add_conditional_edges("replan", platform_fan_out, ["linkedin_agent", "x_agent", "instagram_agent"])

    return graph.compile()


# Module-level compiled graph (imported by main.py)
compiled_graph = build_graph()
