"""
STEP 6: Automated tests using fake LLMs (RunnableLambda) — no real API
calls, no GROQ_API_KEY needed, no cost, deterministic. Real LLM output
quality is verified manually (see README "Example runs" section) since
that's inherently non-deterministic and not suitable for a hard assertion.
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import httpx
import pytest
from groq import RateLimitError
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from chain import generate_linkedin_post

FAKE_POST_WITH_HASHTAGS = (
    "Did you know AI now assists in 1 in 3 hospital diagnoses?\n\n"
    "AI in Healthcare is transforming diagnostics and patient care.\n\n"
    "---HASHTAGS---\n"
    "#AI #Healthcare #Innovation #FutureOfWork"
)


def _fake_llm(response_text: str) -> RunnableLambda:
    return RunnableLambda(lambda prompt_value: AIMessage(content=response_text))


def _fake_rate_limit_error() -> RateLimitError:
    fake_response = httpx.Response(status_code=429, request=httpx.Request("POST", "https://api.groq.com"))
    return RateLimitError("rate limited", response=fake_response, body=None)


def test_returns_non_error_result_for_valid_input():
    result = generate_linkedin_post("AI in Healthcare", "English", llm=_fake_llm(FAKE_POST_WITH_HASHTAGS))
    assert result["error"] is False


def test_output_post_is_non_empty():
    result = generate_linkedin_post("AI in Healthcare", "English", llm=_fake_llm(FAKE_POST_WITH_HASHTAGS))
    assert result["post"].strip() != ""


def test_hashtags_are_correctly_parsed_and_stripped_from_post():
    result = generate_linkedin_post("AI in Healthcare", "English", llm=_fake_llm(FAKE_POST_WITH_HASHTAGS))
    assert result["hashtags"] == ["#AI", "#Healthcare", "#Innovation", "#FutureOfWork"]
    assert "---HASHTAGS---" not in result["post"]
    assert "#AI" not in result["post"]  # hashtags shouldn't leak into the post text


def test_paragraph_count_is_roughly_right():
    result = generate_linkedin_post("AI in Healthcare", "English", llm=_fake_llm(FAKE_POST_WITH_HASHTAGS))
    paragraphs = [p for p in result["post"].split("\n\n") if p.strip()]
    assert 1 <= len(paragraphs) <= 4


def test_missing_hashtag_delimiter_degrades_gracefully():
    result = generate_linkedin_post("Some Topic", "English", llm=_fake_llm("Just a post, no delimiter."))
    assert result["error"] is False
    assert result["hashtags"] == []
    assert result["post"] == "Just a post, no delimiter."


def test_empty_topic_is_rejected_before_calling_the_llm():
    def _explode(_prompt_value):
        raise AssertionError("LLM should never be called for an empty topic")

    result = generate_linkedin_post("", "English", llm=RunnableLambda(_explode))
    assert result["error"] is True
    assert "topic" in result["post"].lower()


def test_empty_language_is_rejected_before_calling_the_llm():
    def _explode(_prompt_value):
        raise AssertionError("LLM should never be called for an empty language")

    result = generate_linkedin_post("AI in Healthcare", "", llm=RunnableLambda(_explode))
    assert result["error"] is True
    assert "language" in result["post"].lower()


def test_persistent_rate_limit_retries_once_then_returns_friendly_message(monkeypatch):
    import chain as chain_module

    monkeypatch.setattr(chain_module, "RATE_LIMIT_RETRY_DELAY_SECONDS", 0.01)

    call_count = {"n": 0}

    def _always_rate_limited(_prompt_value):
        call_count["n"] += 1
        raise _fake_rate_limit_error()

    result = generate_linkedin_post("AI", "English", llm=RunnableLambda(_always_rate_limited))

    assert call_count["n"] == 2  # 1 attempt + 1 retry, not more
    assert result["error"] is True
    assert "rate limit" in result["post"].lower()


def test_transient_rate_limit_succeeds_on_retry(monkeypatch):
    import chain as chain_module

    monkeypatch.setattr(chain_module, "RATE_LIMIT_RETRY_DELAY_SECONDS", 0.01)

    call_count = {"n": 0}

    def _rate_limited_once(_prompt_value):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise _fake_rate_limit_error()
        return AIMessage(content=FAKE_POST_WITH_HASHTAGS)

    result = generate_linkedin_post("AI", "English", llm=RunnableLambda(_rate_limited_once))

    assert call_count["n"] == 2
    assert result["error"] is False
    assert result["hashtags"] == ["#AI", "#Healthcare", "#Innovation", "#FutureOfWork"]


def test_other_llm_exceptions_are_converted_to_friendly_message_not_raised():
    def _explode_with_timeout(_prompt_value):
        raise TimeoutError("simulated network timeout")

    result = generate_linkedin_post("AI in Healthcare", "English", llm=RunnableLambda(_explode_with_timeout))
    assert result["error"] is True
    assert "TimeoutError" in result["post"]


def test_topic_and_language_whitespace_is_stripped():
    captured = {}

    def _record_and_respond(prompt_value):
        captured["prompt_value"] = prompt_value
        return AIMessage(content="ok\n---HASHTAGS---\n#Test")

    generate_linkedin_post("  AI in Healthcare  ", "  English  ", llm=RunnableLambda(_record_and_respond))

    rendered_human_message = captured["prompt_value"].messages[-1].content
    assert "  AI in Healthcare  " not in rendered_human_message
    assert "AI in Healthcare" in rendered_human_message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
