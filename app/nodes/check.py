"""
CHECK node — Content Review Agent.

Scores each platform post against the original content plan.
Populates feedback and overall_score. Does NOT set approval_status —
that decision belongs to routing.py.
"""
import json
from app.core.llm import invoke_cached, usage_delta
from app.core.logger import logger
from app.state.state import ContentState
from app.prompts.check_prompts import CHECK_SYSTEM, CHECK_HUMAN
from app.tools.content_guidelines_checker import content_guidelines_checker


def check_node(state: ContentState) -> ContentState:
    logger.info("[CHECK] Review Agent scoring posts (iteration %d)...", state["iteration_count"] + 1)
    posts = state.get("posts", {})
    response = invoke_cached(
        system_text=CHECK_SYSTEM,
        human_text=CHECK_HUMAN.format(
            content_plan=state["content_plan"],
            posts=json.dumps(posts, indent=2),
        ),
        logger=logger,
    )
    raw = response.content.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        review = json.loads(raw)
    except json.JSONDecodeError:
        review = {
            "linkedin": {"score": 5, "issues": "Parse error", "suggestions": raw},
            "x":        {"score": 5, "issues": "Parse error", "suggestions": raw},
            "instagram":{"score": 5, "issues": "Parse error", "suggestions": raw},
            "overall_score": 5.0,
        }

    feedback = {
        platform: (
            f"Score {review[platform]['score']}/10 | "
            f"Issues: {review[platform]['issues']} | "
            f"Suggestions: {review[platform]['suggestions']}"
        )
        for platform in ("linkedin", "x", "instagram")
        if platform in review
    }

    overall = float(review.get("overall_score", 5.0))

    # ── Deterministic guidelines check (runs alongside LLM scorer) ───────────
    guidelines = content_guidelines_checker.invoke({"posts": posts})
    for platform in ("linkedin", "x", "instagram"):
        result = guidelines.get(platform, {})
        if result.get("violations"):
            violations_str = "; ".join(result["violations"])
            logger.warning("[CHECK] %s guideline violations: %s", platform, violations_str)
            # Append violations to feedback so the platform agent can fix them
            if platform in feedback:
                feedback[platform] += f" | Guideline violations: {violations_str}"
        if result.get("warnings"):
            logger.debug("[CHECK] %s guideline warnings: %s", platform, "; ".join(result["warnings"]))

    logger.info("[CHECK] overall_score=%.1f | guidelines_passed=%s | platforms scored: %s",
                overall, guidelines.get("overall_passed"), list(feedback.keys()))
    for platform, fb in feedback.items():
        logger.debug("[CHECK] %s → %s", platform, fb)

    new_state = dict(state)
    new_state["token_usage"] = usage_delta(response)
    new_state["feedback"] = feedback
    new_state["previous_score"] = state.get("overall_score", 0.0)  # save before overwriting
    new_state["overall_score"] = overall
    new_state["iteration_count"] = state["iteration_count"] + 1
    new_state["history"] = [
        f"[CHECK] Iteration {state['iteration_count'] + 1}: overall_score={overall:.1f}"
    ]
    return new_state
