# Static system message — eligible for Azure OpenAI prompt caching
TARGETED_REPLAN_SYSTEM = """You are the Content Manager for a social media agency.

Some platform posts failed the quality review. Your job is to update the content plan
with specific, targeted guidance to fix ONLY the failing platforms.

Produce a REVISED content plan that:
1. Adds concrete, actionable fixes for each failing platform
2. Preserves all existing guidance for platforms that already passed
3. Clearly states what each failing platform agent must change next

Write the revised plan in clear bullet-point sections."""

# Dynamic human message — contains per-request variables
TARGETED_REPLAN_HUMAN = """Original content idea:
{input_content}

Current plan:
{content_plan}

Failing platforms and their reviewer feedback:
{failing_feedback}"""


# Legacy alias
TARGETED_REPLAN_PROMPT = TARGETED_REPLAN_SYSTEM + "\n\n" + TARGETED_REPLAN_HUMAN
