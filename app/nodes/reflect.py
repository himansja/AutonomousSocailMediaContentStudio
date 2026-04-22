"""
REFLECT node — Feedback consolidation for the refinement loop.

In the parallel architecture, Reflect does NOT rewrite posts itself.
Instead it acts as a pass-through that preserves the check feedback in
state, then the graph re-fans out to the three parallel platform agents
so each can address its own platform-specific feedback independently.
"""
from app.state.state import ContentState


def reflect_node(state: ContentState) -> ContentState:
    """
    Pass-through node. Feedback is already in state["feedback"] from check_node.
    The platform agents read it via _build_feedback_section in act.py.
    """
    new_state = dict(state)
    new_state["history"] = [
        f"[REFLECT] Feedback consolidated, re-dispatching platform agents "
        f"(iteration {state['iteration_count']})."
    ]
    return new_state

