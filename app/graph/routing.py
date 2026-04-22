"""
Routing logic for the Plan -> Fan-out -> Review loop.

After every review, the workflow either:
    - approves and ends, or
    - replans and sends work back to the parallel platform agents.
"""
from app.core.logger import logger
from app.state.state import ContentState


QUALITY_THRESHOLD = 7.5


def should_continue(state: ContentState) -> str:
    """
    Returns 'approve' or 'replan'.
    - 'approve' → graph routes directly to END
    - 'replan' → graph routes to the manager replan node, then fans out again
    Approval is forced once max_iterations is reached.
    """
    iteration_count = state["iteration_count"]
    max_iterations = state.get("max_iterations", 3)
    overall_score = state.get("overall_score", 0.0)

    if iteration_count >= max_iterations:
        logger.warning("[ROUTE] Max iterations (%d) reached — forcing approval (score=%.1f)",
                       max_iterations, overall_score)
        return "approve"

    if overall_score >= QUALITY_THRESHOLD:
        logger.info("[ROUTE] Quality threshold met (score=%.1f >= %.1f) — approving",
                    overall_score, QUALITY_THRESHOLD)
        return "approve"

    logger.info("[ROUTE] Score %.1f below threshold %.1f — replanning (iteration %d/%d)",
                overall_score, QUALITY_THRESHOLD, iteration_count, max_iterations)
    return "replan"
