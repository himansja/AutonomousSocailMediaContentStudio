import os
from dataclasses import dataclass
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

load_dotenv()

_REQUIRED = {
    "AZURE_OPENAI_ENDPOINT": os.getenv("AZURE_OPENAI_ENDPOINT"),
    "AZURE_OPENAI_API_KEY": os.getenv("AZURE_OPENAI_API_KEY"),
    "AZURE_OPENAI_DEPLOYMENT_NAME": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
    "AZURE_OPENAI_API_VERSION": os.getenv("AZURE_OPENAI_API_VERSION"),
}

_missing = [key for key, val in _REQUIRED.items() if not val]
if _missing:
    raise EnvironmentError(
        f"Missing required environment variable(s): {', '.join(_missing)}. "
        "Set them in your .env file or shell environment before starting the app."
    )

llm = AzureChatOpenAI(
    azure_endpoint=_REQUIRED["AZURE_OPENAI_ENDPOINT"],
    api_key=_REQUIRED["AZURE_OPENAI_API_KEY"],
    azure_deployment=_REQUIRED["AZURE_OPENAI_DEPLOYMENT_NAME"],
    api_version=_REQUIRED["AZURE_OPENAI_API_VERSION"],
    temperature=0.7,
    max_retries=3,
    model_kwargs={
        # Critical for cache routing
        "prompt_cache_key": "langchain-prompt-caching"
    }
)

# ---------------------------------------------------------------------------
# Shared static cache anchor — prepended to every system message.
# Azure OpenAI requires a minimum 1 024-token identical prefix before it will
# activate automatic prompt caching.  All agents share this anchor so every
# call benefits once the prefix is warm in the cache.
# ---------------------------------------------------------------------------
_CACHE_ANCHOR = """\
=== AURORA CONTENT STUDIO — AGENCY BRIEF, QUALITY STANDARDS & PLATFORM GUIDE ===

AGENCY IDENTITY
Aurora Content Studio transforms complex ideas into compelling, platform-native social
media content for forward-thinking brands. Every piece of content we produce must
educate, inspire, and drive measurable engagement while staying true to the brand voice.

BRAND VOICE PILLARS
1. Authoritative yet Accessible  — cite facts and data; never talk down to the audience.
2. Human-First                   — write person-to-person, not brand-to-demographic.
3. Action-Oriented               — every post ends with a clear next step or takeaway.
4. Culturally Aware              — stay current with platform trends without chasing fads.
5. Inclusive                     — bias-free language, global-friendly, jargon-light.
6. Specific over Vague           — "37% of marketers" beats "many marketers" every time.

PLATFORM SPECIFICATIONS

LinkedIn
  Character limit : 3 000 characters (body); optimal body length 900–1 400 chars.
  Hook            : First 2 lines (≤ 210 chars) must compel readers to click "see more".
  Hashtags        : 3–5 relevant tags, appended at the end, each on its own line.
  Tone            : Professional, thought-leadership, first-person narrative or data-driven.
  Emoji           : 0–2 per post; used only to highlight key bullet points.
  Links           : Do NOT embed URLs in the post body (use the LinkedIn link field).
  Structure       : Hook → Story/Data → Insight → CTA.

X / Twitter
  Character limit : HARD 280 characters INCLUDING spaces, punctuation, and emoji.
  Hashtags        : Maximum 2 (they count toward the 280-char limit).
  Tone            : Punchy, witty, or provocative — the first word must earn attention.
  Format          : Single tweet only unless explicitly instructed to thread.
  Links           : Count as 23 chars regardless of actual URL length.
  Emoji           : 1–2 maximum; prefer text-forward hooks.
  Structure       : Hook (first 3 words) → Insight → Hashtags.

Instagram
  Character limit : 2 200 characters; first 125 chars appear before the "more" fold.
  Hashtags        : 5–15, appended after 5 blank lines at the end of the caption.
  Tone            : Aspirational, conversational, community-driven; use "you / your" framing.
  Emoji           : 2–6 per post; use to add warmth and visual line breaks.
  CTA             : Must include a question or direct call-to-action in the final sentence.
  Structure       : Opening hook → Story or context → Value statement → CTA → Hashtags.

QUALITY STANDARDS — every post must satisfy ALL criteria before it is approved
QS-1  Accuracy        : No unverified claims; all statistics come from the provided research.
QS-2  Originality     : No recycled phrases, clichés, or boilerplate copy.
QS-3  Platform-fit    : Tone, length, and format exactly match the target platform spec above.
QS-4  Message fidelity: The core message from the content plan must be clearly present.
QS-5  Engagement hook : An irresistible hook in the opening line (or first 3 words for X).
QS-6  CTA/Conclusion  : Post ends with a clear next step, question, or memorable close.
QS-7  Grammar & style : Error-free; active voice preferred; no passive constructions.
QS-8  Brand safety    : No controversial politics, hate speech, explicit content, or FUD.
QS-9  Hashtag quality : Mid-range hashtags (10 K–500 K posts) preferred over mega-tags.
QS-10 Specificity     : Concrete facts and numbers included wherever the research supports it.

CONTENT STRATEGY PRINCIPLES
• Lead with value, follow with proof — state the key insight first, support with data.
• Social proof and community language increase reshares on LinkedIn and Instagram.
• Controversy-lite hooks (contrarian takes, counterintuitive data) spike X engagement.
• Always tie trending context back to the core message to avoid an opportunistic tone.
• Avoid over-promotion — educational and inspirational posts outperform sales-first content.
• Posts that ask a question in the CTA receive significantly more comment-section engagement.

REVIEW SCORING RUBRIC (used by the Content Review Agent)
Score 9–10 : Exceptional. Exceeds platform best practices; highly shareable; no changes needed.
Score 7–8  : Good. Meets all QS criteria; minor polish could lift engagement further.
Score 5–6  : Acceptable. One or two QS criteria partially unmet; revision recommended.
Score 3–4  : Below standard. Multiple QS criteria unmet; significant rework required.
Score 0–2  : Unacceptable. Fundamentally misaligned with content plan or platform constraints.

IMPORTANT OPERATING RULES
- You will be given a specific role and task after this agency brief.
- Always follow your specific role instructions precisely.
- Never output content that violates QS-8 (brand safety).
- When in doubt, favour clarity and specificity over cleverness.

=== END OF AGENCY BRIEF ===

"""


@dataclass
class LLMResult:
    """
    Return value of invoke_cached, encapsulating the model's text reply, token usage details, cache status, and raw message.

    Attributes:
        content       : the model's text reply (str, ready to .strip())
        usage         : token counts matching the S9 demo-1 'usage' dict:
                          prompt_tokens, completion_tokens, total_tokens,
                          prompt_tokens_details.cached_tokens
        cache_status  : "HIT" if cached_tokens > 0, else "MISS"
        message       : the raw LangChain AIMessage (for response_metadata etc.)
    """
    content: str
    usage: dict
    cache_status: str
    message: AIMessage


def invoke_cached(system_text: str, human_text: str, logger=None) -> LLMResult:
    """
    Invoke the LLM with a system + human message, using the shared static cache anchor for optimal Azure caching.:
      - system_text : static agent persona/instructions  → eligible for Azure cache
      - human_text  : dynamic per-request content       → never cached

    Returns LLMResult with .content, .usage, .cache_status, and raw .message.
    """
    messages = [
        SystemMessage(content=_CACHE_ANCHOR + system_text),
        HumanMessage(content=human_text),
    ]
    response = llm.invoke(messages)

    usage_raw = response.response_metadata.get("token_usage", {})
    cached_tokens = (
        usage_raw.get("prompt_tokens_details", {})
                 .get("cached_tokens", 0)
    )
    cache_status = "HIT" if cached_tokens > 0 else "MISS"

    usage = {
        "prompt_tokens": usage_raw.get("prompt_tokens", 0),
        "completion_tokens": usage_raw.get("completion_tokens", 0),
        "total_tokens": usage_raw.get("total_tokens", 0),
        "prompt_tokens_details": {
            "cached_tokens": cached_tokens,
        },
    }

    if logger is not None:
        logger.debug(
            "[CACHE] %s | cached=%d / prompt=%d / completion=%d / total=%d tokens",
            cache_status,
            cached_tokens,
            usage["prompt_tokens"],
            usage["completion_tokens"],
            usage["total_tokens"],
        )

    return LLMResult(
        content=str(response.content),
        usage=usage,
        cache_status=cache_status,
        message=response,
    )


def usage_delta(result: "LLMResult") -> dict:
    """Return a token-usage delta dict for accumulation in ContentState."""
    return {
        "prompt_tokens":     result.usage["prompt_tokens"],
        "completion_tokens": result.usage["completion_tokens"],
        "total_tokens":      result.usage["total_tokens"],
        "cached_tokens":     result.usage["prompt_tokens_details"]["cached_tokens"],
        "cache_hits":        1 if result.cache_status == "HIT" else 0,
        "cache_misses":      0 if result.cache_status == "HIT" else 1,
    }
