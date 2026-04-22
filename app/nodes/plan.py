"""
PLAN and REPLAN nodes for the Content Manager.

`plan_node` creates the initial strategy from the raw idea.
`replan_node` revises that strategy after review feedback and sends the
workflow back through the parallel platform agents.
"""
from app.core.llm import llm
from app.state.state import ContentState


PLAN_PROMPT = """You are the Content Manager for a social media agency.

Analyse the content idea below and produce a detailed content PLAN that will
guide platform-specific writers. Do NOT write the posts yet.

Content idea:
{input_content}

Your plan must cover:
1. Target audience (who will read this)
2. Core message (one sentence that every post must convey)
3. LinkedIn strategy  — tone, length, structure, professional angle, hashtag themes
4. X (Twitter) strategy — hook style, character constraints, viral angle, hashtag themes
5. Instagram strategy  — visual cue suggestions, storytelling angle, CTA type, hashtag themes
6. Key facts / phrases that must appear in all posts
7. What to AVOID (off-brand language, over-promotion, etc.)

Write the plan in clear bullet-point sections. Be specific and actionable.
"""

REPLAN_PROMPT = """You are the Content Manager for a social media agency.

The current social media strategy needs revision after review feedback.
Update the plan so the platform agents can produce stronger outputs.

Original content idea:
{input_content}

Current plan:
{content_plan}

Reviewer feedback:
{feedback}

Produce a REVISED content plan that:
1. Fixes the weaknesses identified by the reviewer
2. Preserves the original core message
3. Gives clearer, more actionable platform-specific guidance
4. Highlights what each platform agent must change next

Write the revised plan in clear bullet-point sections. Be specific and actionable.
"""


def plan_node(state: ContentState) -> ContentState:
    prompt = PLAN_PROMPT.format(input_content=state["input_content"])
    response = llm.invoke(prompt)
    content_plan = response.content.strip()

    new_state = dict(state)
    new_state["content_plan"] = content_plan
    new_state["posts"] = {}
    new_state["feedback"] = {}
    new_state["overall_score"] = 0.0
    new_state["final_output"] = ""
    new_state["iteration_count"] = 0
    new_state["approval_status"] = False
    new_state["history"] = ["[PLAN] Initial content strategy created."]
    return new_state


def replan_node(state: ContentState) -> ContentState:
    prompt = REPLAN_PROMPT.format(
        input_content=state["input_content"],
        content_plan=state.get("content_plan", ""),
        feedback=state.get("feedback", {}),
    )
    response = llm.invoke(prompt)
    revised_plan = response.content.strip()

    new_state = dict(state)
    new_state["content_plan"] = revised_plan
    new_state["final_output"] = ""
    new_state["history"] = [
        f"[REPLAN] Strategy revised after review iteration {state['iteration_count']}."
    ]
    return new_state
