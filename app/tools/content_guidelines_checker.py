"""
content_guidelines_checker tool — deterministic rule-based validation.

Runs alongside the LLM scorer in check_node to catch hard rule violations
that an LLM might overlook or score inconsistently.

Rules checked per platform:
  linkedin  — word count 100-400, at least 1 hashtag
  x         — char count ≤ 280, at least 1 hashtag
  instagram — word count 50-250, at least 3 hashtags, contains a CTA keyword
"""
from langchain_core.tools import tool
import re


# ── Platform rule definitions ─────────────────────────────────────────────────

_CTA_KEYWORDS = [
    "link in bio", "click", "visit", "sign up", "join", "learn more",
    "get started", "download", "follow", "share", "comment", "tag",
    "check out", "discover", "explore", "register",
]

_PLATFORM_RULES = {
    "linkedin": {
        "min_words": 100,
        "max_words": 400,
        "min_hashtags": 1,
        "max_chars": None,
        "require_cta": False,
    },
    "x": {
        "min_words": 1,
        "max_words": None,
        "min_hashtags": 1,
        "max_chars": 280,
        "require_cta": False,
    },
    "instagram": {
        "min_words": 50,
        "max_words": 250,
        "min_hashtags": 3,
        "max_chars": None,
        "require_cta": True,
    },
}


def _count_hashtags(text: str) -> int:
    return len(re.findall(r"#\w+", text))


def _count_words(text: str) -> int:
    return len(text.split())


def _has_cta(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in _CTA_KEYWORDS)


def _check_platform(platform: str, post: str) -> dict:
    rules = _PLATFORM_RULES.get(platform)
    if not rules:
        return {"passed": True, "violations": [], "warnings": []}

    violations = []
    warnings = []
    word_count = _count_words(post)
    char_count = len(post)
    hashtag_count = _count_hashtags(post)

    if rules["min_words"] and word_count < rules["min_words"]:
        violations.append(
            f"Too short: {word_count} words (min {rules['min_words']})"
        )
    if rules["max_words"] and word_count > rules["max_words"]:
        warnings.append(
            f"Too long: {word_count} words (max {rules['max_words']})"
        )
    if rules["max_chars"] and char_count > rules["max_chars"]:
        violations.append(
            f"Exceeds char limit: {char_count} chars (max {rules['max_chars']})"
        )
    if hashtag_count < rules["min_hashtags"]:
        violations.append(
            f"Too few hashtags: {hashtag_count} (min {rules['min_hashtags']})"
        )
    if rules["require_cta"] and not _has_cta(post):
        violations.append("Missing Call-To-Action")

    return {
        "passed": len(violations) == 0,
        "violations": violations,
        "warnings": warnings,
        "stats": {
            "word_count": word_count,
            "char_count": char_count,
            "hashtag_count": hashtag_count,
        },
    }


@tool
def content_guidelines_checker(posts: dict) -> dict:
    """
    Run deterministic guideline checks on a dict of platform posts.

    Args:
        posts: dict mapping platform name to post text,
               e.g. {"linkedin": "...", "x": "...", "instagram": "..."}

    Returns a dict mapping each platform to its check result:
      {
        "linkedin": {"passed": bool, "violations": [...], "warnings": [...], "stats": {...}},
        "x":        {...},
        "instagram": {...},
        "overall_passed": bool   # True only if ALL platforms passed
      }
    """
    results = {}
    for platform, post in posts.items():
        results[platform] = _check_platform(platform, post)

    results["overall_passed"] = all(
        v["passed"] for k, v in results.items() if k != "overall_passed"
    )
    return results
