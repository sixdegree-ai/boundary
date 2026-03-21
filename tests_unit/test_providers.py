"""Tests for provider resolution."""

import os

import pytest

from bench.providers import AnthropicProvider, GeminiProvider, OpenAIProvider, XAIProvider, get_provider

has_anthropic_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
has_openai_key = bool(os.environ.get("OPENAI_API_KEY"))
has_xai_key = bool(os.environ.get("XAI_API_KEY"))
has_google_key = bool(os.environ.get("GOOGLE_API_KEY"))


@pytest.mark.skipif(not has_anthropic_key, reason="ANTHROPIC_API_KEY not set")
def test_get_provider_anthropic():
    p = get_provider("claude-sonnet")
    assert isinstance(p, AnthropicProvider)
    assert p.model == "claude-sonnet-4-20250514"


@pytest.mark.skipif(not has_openai_key, reason="OPENAI_API_KEY not set")
def test_get_provider_openai():
    p = get_provider("gpt-4o")
    assert isinstance(p, OpenAIProvider)
    assert p.model == "gpt-4o"


@pytest.mark.skipif(not has_xai_key, reason="XAI_API_KEY not set")
def test_get_provider_xai():
    p = get_provider("grok-3")
    assert isinstance(p, XAIProvider)
    assert p.model == "grok-3"


@pytest.mark.skipif(not has_google_key, reason="GOOGLE_API_KEY not set")
def test_get_provider_gemini():
    p = get_provider("gemini-flash")
    assert isinstance(p, GeminiProvider)
    assert p.model == "gemini-2.5-flash"


@pytest.mark.skipif(not has_anthropic_key, reason="ANTHROPIC_API_KEY not set")
def test_get_provider_full_name():
    p = get_provider("claude-opus-4-20250514")
    assert isinstance(p, AnthropicProvider)
    assert p.model == "claude-opus-4-20250514"


def test_get_provider_unknown():
    with pytest.raises(ValueError, match="Unknown provider"):
        get_provider("llama-3")
