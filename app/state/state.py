from typing import Annotated, Dict, TypedDict


def merge_dicts(old, new):
    return {**old, **new}


def append_list(old, new):
    return old + new


def sum_usage(old: dict, new: dict) -> dict:
    """Accumulate token-usage deltas across all LLM calls in the workflow."""
    return {
        "prompt_tokens":     old.get("prompt_tokens", 0)     + new.get("prompt_tokens", 0),
        "completion_tokens": old.get("completion_tokens", 0) + new.get("completion_tokens", 0),
        "total_tokens":      old.get("total_tokens", 0)      + new.get("total_tokens", 0),
        "cached_tokens":     old.get("cached_tokens", 0)     + new.get("cached_tokens", 0),
        "cache_hits":        old.get("cache_hits", 0)        + new.get("cache_hits", 0),
        "cache_misses":      old.get("cache_misses", 0)      + new.get("cache_misses", 0),
    }


class ContentState(TypedDict):
    # ── Input ────────────────────────────────────────────────────────────────
    input_content: str
    source_url: str           # Optional URL to a blog post / article
    uploaded_file_path: str   # Optional path to an uploaded file

    # ── Plan stage ───────────────────────────────────────────────────────────
    content_plan: str          # Strategy/plan produced by the Planner LLM
    search_results: str        # Raw research context fetched before planning

    # ── Act stage ────────────────────────────────────────────────────────────
    posts: Annotated[Dict[str, str], merge_dicts]   # {linkedin, x, instagram}

    # ── Check stage ──────────────────────────────────────────────────────────
    feedback: Annotated[Dict[str, str], merge_dicts]  # per-platform review
    overall_score: float       # aggregated quality score from Checker
    previous_score: float      # overall_score from the prior iteration (used to detect no-improvement)

    # ── Format stage ─────────────────────────────────────────────────────────
    final_output: str          # clean publish-ready output from Formatter LLM

    # ── Token usage (accumulated across all LLM calls) ───────────────────────
    token_usage: Annotated[dict, sum_usage]

    # ── Control ──────────────────────────────────────────────────────────────
    # ── Reflect stage ────────────────────────────────────────────────────────
    platforms_to_retry: list  # subset of [linkedin, x, instagram] that failed review

    # ── Control ──────────────────────────────────────────────────────────────
    history: Annotated[list, append_list]
    approval_status: bool
    iteration_count: int
    max_iterations: int