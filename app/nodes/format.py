"""
FORMAT node — Output Formatter LLM (additional layer).

This is a dedicated LLM call that takes the approved posts and
transforms them into a clean, structured, publish-ready content package.
It handles final polish: consistent hashtag ordering, emoji placement,
line-break formatting, and a summary cover note.
"""
import json
from app.core.llm import llm
from app.state.state import ContentState


FORMAT_PROMPT = """You are a Content Publishing Formatter. Your only job is to take
approved social media posts and produce a final, publish-ready content package.

Approved posts:
{posts}

Content strategy summary:
{content_plan_summary}

Quality achieved: {overall_score}/10 after {iteration_count} review cycle(s).

Format the final output as a clean text document with clearly labelled sections.
Apply these formatting rules:
- LinkedIn: professional paragraph structure, hashtags on a new line at the end
- X (Twitter): single block, confirm it is within 280 chars, hashtags inline
- Instagram: caption body first, double line break, then all hashtags grouped
- Add a one-paragraph "Publishing Note" at the top summarising the content theme
  and recommended posting time for each platform
- Do NOT change the wording of the posts — only format and polish

Return the formatted document as plain text (not JSON).
"""


def format_node(state: ContentState) -> ContentState:
    # Summarise the plan to first 500 chars to keep the prompt tight
    plan_summary = state["content_plan"][:500] + (
        "..." if len(state["content_plan"]) > 500 else ""
    )

    prompt = FORMAT_PROMPT.format(
        posts=json.dumps(state["posts"], indent=2),
        content_plan_summary=plan_summary,
        overall_score=round(state.get("overall_score", 0.0), 1),
        iteration_count=state["iteration_count"],
    )
    response = llm.invoke(prompt)
    final_output = response.content.strip()

    new_state = dict(state)
    new_state["final_output"] = final_output
    new_state["approval_status"] = True
    new_state["history"] = ["[FORMAT] Final publish-ready package produced."]
    return new_state
