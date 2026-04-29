"""
read_url_tool — fetches and extracts the main text from a web page.

Used by the plan_node to pull in a blog post (or any URL) supplied by the user
as the primary source material for social media content generation.
"""
from html.parser import HTMLParser
from urllib.error import URLError
from urllib.request import Request, urlopen

from langchain_core.tools import tool


# Tags whose inner text we always skip (navigation, scripts, styles, etc.)
_SKIP_TAGS = frozenset(
    {"script", "style", "nav", "footer", "header", "aside", "noscript"}
)


class _TextExtractor(HTMLParser):
    """Minimal HTML-to-text extractor using only stdlib."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._texts: list[str] = []
        self._depth: int = 0  # nesting depth inside skip-tags

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in _SKIP_TAGS:
            self._depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS and self._depth > 0:
            self._depth -= 1

    def handle_data(self, data: str) -> None:
        if self._depth == 0:
            stripped = data.strip()
            if stripped:
                self._texts.append(stripped)

    def get_text(self) -> str:
        return "\n".join(self._texts)


@tool
def read_url(url: str, max_chars: int = 8000) -> str:
    """
    Fetch and extract the main text content from a web page (e.g., a blog post).

    Args:
        url: Full URL to fetch (must start with http:// or https://).
        max_chars: Maximum characters to return (default 8000).

    Returns the extracted text content of the page, or an error message.
    """
    if not url.startswith(("http://", "https://")):
        return "Invalid URL: must start with http:// or https://"

    req = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; ContentStudioBot/1.0)"
            )
        },
    )
    try:
        with urlopen(req, timeout=15) as resp:  # noqa: S310 — URL validated above
            html = resp.read().decode("utf-8", errors="ignore")
    except URLError as exc:
        return f"Error fetching URL: {exc}"
    except Exception as exc:
        return f"Unexpected error fetching URL: {exc}"

    extractor = _TextExtractor()
    extractor.feed(html)
    text = extractor.get_text()

    if not text.strip():
        return "No readable text found at the provided URL."

    return text[:max_chars]
