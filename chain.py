"""
STEP 3: Chain construction (LCEL) + rate-limit-aware error handling.

WHY GROQ
---------
Groq was chosen over other free-tier options because:
- It has a genuine ONGOING free tier (not a one-time trial credit that
  expires) — no credit card required at signup.
- Its free tier for llama-3.3-70b-versatial gives 30 requests/minute and
  1,000 requests/day, which comfortably covers interactive demo use and
  grading without hitting limits under normal use (see README for the
  full published numbers and their source).
- Groq's LPU hardware makes inference very fast — noticeably snappier in
  a live Streamlit demo than many alternatives, which matters for UX.

WHY LCEL, NOT THE OLDER LLMChain CLASS
-----------------------------------------
`prompt | llm | output_parser` is LangChain's current recommended pattern.
The older `LLMChain` class still works but is considered legacy — LCEL
chains get streaming, batching, and async support automatically, with no
extra code, which `LLMChain` doesn't consistently provide.

TOKEN-EFFICIENT DESIGN
-------------------------
- Single-turn: no conversation history is stored or resent — every call is
  independent, so token cost doesn't grow across a session.
- `max_tokens` is capped (see ChatGroq below) to roughly what a 2-4
  paragraph post + hashtags actually needs, so a runaway generation can't
  silently burn through the TPM budget.
- The system prompt (prompts.py) is deliberately concise.

RATE-LIMIT HANDLING
----------------------
We catch `groq.RateLimitError` SPECIFICALLY (not a bare `except Exception`)
so a 429 gets a clear, honest "you've hit the free-tier limit, wait a
moment" message — then we retry ONCE after a short fixed backoff, since
Groq's free tier resets on a rolling per-minute window, so a few seconds'
wait often resolves it. If the retry also fails, we give up and return the
friendly message rather than looping indefinitely.
"""

import time

from dotenv import load_dotenv
from groq import RateLimitError
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq

from prompts import HASHTAG_DELIMITER, linkedin_post_prompt

# Loaded at MODULE level (not just in __main__) so .env is read before
# anything tries to construct an LLM client — this matters because app.py
# imports this module, and if load_dotenv() only ran in this file's
# __main__ block, app.py would never trigger it.
load_dotenv()

_output_parser = StrOutputParser()

# Built LAZILY (on first real use, not at import time): ChatGroq validates
# credentials immediately on construction and raises if no API key is set
# yet, so building it at module level would make merely IMPORTING this
# file crash in any environment without a key already configured (e.g. a
# test runner). Building it on first actual call avoids that entirely.
_llm = None

RATE_LIMIT_RETRY_DELAY_SECONDS = 3


def _get_llm():
    global _llm
    if _llm is None:
        _llm = ChatGroq(
            model="openai/gpt-oss-20b",
            temperature=0.7,  # some creative variety in phrasing/hooks
            max_tokens=800,   # enough for a 2-4 paragraph post + hashtags,
                               # capped so a runaway generation can't burn TPM budget
        )
    return _llm


def _build_chain(llm):
    """Composes the LCEL chain. Takes `llm` as a parameter (rather than
    reading a module-level global) so tests can pass in a fake LLM instead
    of a real one — see tests/test_chain.py."""
    return linkedin_post_prompt | llm | _output_parser


def _parse_post_and_hashtags(raw_output: str) -> tuple[str, list[str]]:
    """Splits the raw LLM output into (post_text, hashtags_list) using the
    delimiter line defined in prompts.py. Handles the case where the model
    doesn't follow the delimiter instruction exactly, so a formatting slip
    degrades gracefully instead of crashing the app."""
    if HASHTAG_DELIMITER in raw_output:
        post_part, hashtag_part = raw_output.split(HASHTAG_DELIMITER, 1)
    else:
        # Defensive fallback: no delimiter found — treat the whole thing as
        # the post, with no hashtags, rather than raising an error the user
        # would see as a crash.
        post_part, hashtag_part = raw_output, ""

    post_text = post_part.strip()
    hashtags = [tag for tag in hashtag_part.split() if tag.startswith("#")]
    return post_text, hashtags


def generate_linkedin_post(topic: str, language: str, llm=None) -> dict:
    """
    Generates a LinkedIn post for the given topic and language.

    Returns a dict: {"post": str, "hashtags": list[str], "error": bool}.
    `error=True` means `post` holds a user-friendly message, not real
    content — the UI layer (app.py) checks this flag rather than guessing
    from string contents.

    The optional `llm` parameter lets tests inject a fake/mock LLM instead
    of a real API-backed one — see tests/test_chain.py.
    """
    if not topic or not topic.strip():
        return {"post": "⚠️ Please enter a topic before generating a post.", "hashtags": [], "error": True}
    if not language or not language.strip():
        return {"post": "⚠️ Please select or enter a language before generating a post.", "hashtags": [], "error": True}

    active_chain = _build_chain(llm if llm is not None else _get_llm())
    chain_input = {"topic": topic.strip(), "language": language.strip()}

    for attempt in (1, 2):  # one real attempt + one retry on rate limit
        try:
            raw_output = active_chain.invoke(chain_input)
            post_text, hashtags = _parse_post_and_hashtags(raw_output)
            return {"post": post_text, "hashtags": hashtags, "error": False}

        except RateLimitError:
            if attempt == 1:
                time.sleep(RATE_LIMIT_RETRY_DELAY_SECONDS)
                continue
            return {
                "post": (
                    "⚠️ We've hit the free-tier rate limit for the moment. "
                    "Please wait a few seconds and try again."
                ),
                "hashtags": [],
                "error": True,
            }

        except Exception as e:
            # Broad catch for anything else (network issue, auth error,
            # etc.) — the function's contract is "always return a dict the
            # UI can display", never raise and crash the app.
            error_name = type(e).__name__
            return {
                "post": (
                    f"⚠️ Sorry, something went wrong while generating your post "
                    f"({error_name}). Please check your API key/connection and try again.\n\n"
                    f"Details: {e}"
                ),
                "hashtags": [],
                "error": True,
            }


if __name__ == "__main__":
    # Quick manual smoke test: `python chain.py` (needs a real GROQ_API_KEY
    # in your environment/.env).
    result = generate_linkedin_post("AI in Healthcare", "English")
    print("POST:\n", result["post"])
    print("\nHASHTAGS:", result["hashtags"])
