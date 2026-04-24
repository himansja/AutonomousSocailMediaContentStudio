"""
web_search tool — DuckDuckGo search to enrich content planning.

Used by plan_node before building the content strategy, so the LLM
has real-world context: current news, trends, and relevant facts about
the topic the user wants to create social media content for.
"""
from langchain_core.tools import tool
from duckduckgo_search import DDGS


@tool
def web_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search DuckDuckGo for recent information about a topic.

    Args:
        query: search query string
        max_results: number of results to return (default 5, max 10)

    Returns a list of dicts, each with:
      - title (str): page title
      - url (str): source URL
      - snippet (str): short text excerpt from the page
    """
    max_results = min(max_results, 10)  # cap to avoid excessive payloads
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", ""),
            })
    return results
