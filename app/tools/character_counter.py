"""
character_counter tool — deterministic character-count enforcement.

Used by the X (Twitter) agent to validate and trim posts to the 280-char
limit without relying on ad-hoc string slicing in the node.
"""
from langchain_core.tools import tool


X_MAX_CHARS = 280


@tool
def character_counter(text: str, limit: int = X_MAX_CHARS) -> dict:
    """
    Count characters in text and enforce an optional limit.

    Returns a dict with:
      - char_count (int): actual character count
      - limit (int): the limit checked against
      - within_limit (bool): True if char_count <= limit
      - text (str): original text if within limit, trimmed text otherwise
      - trimmed (bool): True if text was shortened to fit
    """
    count = len(text)
    if count <= limit:
        return {
            "char_count": count,
            "limit": limit,
            "within_limit": True,
            "text": text,
            "trimmed": False,
        }

    # Trim to limit, preserving the last word boundary where possible
    trimmed = text[:limit - 3].rsplit(" ", 1)[0] + "..."
    return {
        "char_count": count,
        "limit": limit,
        "within_limit": False,
        "text": trimmed,
        "trimmed": True,
    }
