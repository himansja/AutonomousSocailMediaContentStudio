"""
Routing logic for the Plan -> Fan-out -> Review loop.

After every review, the workflow either:
    - approves and ends, or
    - replans and sends work back to the parallel platform agents.
"""
from app.core.logger import logger
from app.state.state import ContentState


QUALITY_THRESHOLD = 8.8  # Overall score above which content is automatically approved
PLATFORM_FAIL_THRESHOLD = 7.0  # Per-platform score below which that platform is retried; kept lower than QUALITY_THRESHOLD to prevent oscillation


def should_continue(state: ContentState) -> str:
    """
    Returns 'approve' or 'reflect'.
    - 'approve' → graph routes directly to format then END
    - 'reflect' → graph routes to the reflect node, then fans out again

    Early-exit rules (in order):
      1. Max iterations reached → force approve
      2. Score meets threshold → approve
      3. Score did not improve vs previous iteration → approve (no point retrying)
      4. Otherwise → reflect
    """
    iteration_count = state["iteration_count"]
    max_iterations = state.get("max_iterations", 3)
    overall_score = state.get("overall_score", 0.0)
    previous_score = state.get("previous_score", 0.0)

    if iteration_count >= max_iterations:
        logger.warning("[ROUTE] Max iterations (%d) reached — forcing approval (score=%.1f)",
                       max_iterations, overall_score)
        return "approve"

    if overall_score >= QUALITY_THRESHOLD:
        logger.info("[ROUTE] Quality threshold met (score=%.1f >= %.1f) — approving",
                    overall_score, QUALITY_THRESHOLD)
        return "approve"

    if iteration_count > 1 and overall_score <= previous_score:
        logger.warning(
            "[ROUTE] Score did not improve (%.1f → %.1f) — approving to avoid wasted iterations",
            previous_score, overall_score,
        )
        return "approve"

    logger.info("[ROUTE] Score %.1f below threshold %.1f — reflecting (iteration %d/%d)",
                overall_score, QUALITY_THRESHOLD, iteration_count, max_iterations)
    return "reflect"
