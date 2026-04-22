from typing import Annotated, Dict, TypedDict


def merge_dicts(old, new):
    return {**old, **new}


def append_list(old, new):
    return old + new


class ContentState(TypedDict):
    # ── Input ────────────────────────────────────────────────────────────────
    input_content: str

    # ── Plan stage ───────────────────────────────────────────────────────────
    content_plan: str          # Strategy/plan produced by the Planner LLM

    # ── Act stage ────────────────────────────────────────────────────────────
    posts: Annotated[Dict[str, str], merge_dicts]   # {linkedin, x, instagram}

    # ── Check stage ──────────────────────────────────────────────────────────
    feedback: Annotated[Dict[str, str], merge_dicts]  # per-platform review
    overall_score: float       # aggregated quality score from Checker

    # ── Format stage ─────────────────────────────────────────────────────────
    final_output: str          # clean publish-ready output from Formatter LLM

    # ── Control ──────────────────────────────────────────────────────────────
    history: Annotated[list, append_list]
    approval_status: bool
    iteration_count: int
    max_iterations: int