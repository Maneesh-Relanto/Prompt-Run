"""
Tests for all LLM providers.
All external SDK calls are mocked — no real API keys or network needed.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from prompt_run.providers.base import ProviderError, ProviderResponse
from prompt_run.providers import get_provider, PROVIDERS


# ── Shared exception stubs ─────────────────────────────────────────────────────


class _ConnErr(Exception):
    pass


class _AuthErr(Exception):
    pass


class _RateErr(Exception):
    pass


class _StatusErr(Exception):
    def __init__(self, msg: str = "", status_code: int = 500, message: str = "server error"):
        super().__init__(msg)
        self.status_code = status_code
        self.message = message


# ── providers/__init__.py ──────────────────────────────────────────────────────


class TestGetProvider:
    def test_all_known_providers_registered(self):
        assert set(PROVIDERS.keys()) == {"anthropic", "openai", "ollama"}

    def test_unknown_provider_raises_provider_error(self):
        with pytest.raises(ProviderError, match="Unknown provider"):
            get_provider("nonexistent-llm")

    def test_unknown_provider_lists_available(self):
        with pytest.raises(ProviderError, match="anthropic"):
            get_provider("wrong")


# ── AnthropicProvider ──────────────────────────────────────────────────────────


def _make_anthropic(api_key: str = "sk-test") -> tuple:
    """Build an AnthropicProvider with a fully mocked SDK."""
    mock_sdk = MagicMock()
    mock_sdk.APIConnectionError = _ConnErr
    mock_sdk.AuthenticationError = _AuthErr
    mock_sdk.RateLimitError = _RateErr
    mock_sdk.APIStatusError = _StatusErr
    mock_client = MagicMock()
    mock_sdk.Anthropic.return_value = mock_client

    with patch.dict(sys.modules, {"anthropic": mock_sdk}):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": api_key}):
            from prompt_run.providers.anthropic import AnthropicProvider

            provider = AnthropicProvider()

    return provider, mock_sdk, mock_client


class TestAnthropicProvider:
    def test_missing_api_key_raises(self):
        mock_sdk = MagicMock()
        with patch.dict(sys.modules, {"anthropic": mock_sdk}):
            with patch.dict(os.environ, {}, clear=True):
                os.environ.pop("ANTHROPIC_API_KEY", None)
                from prompt_run.providers.anthropic import AnthropicProvider

                with pytest.raises(ProviderError, match="ANTHROPIC_API_KEY"):
                    AnthropicProvider()

    def test_default_model(self):
        provider, _, _ = _make_anthropic()
        assert provider.default_model() == "claude-sonnet-4-6"

    def test_complete_returns_provider_response(self):
        provider, _, mock_client = _make_anthropic()
        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="Hello!")]
        mock_resp.model = "claude-sonnet-4-6"
        mock_resp.usage.input_tokens = 10
        mock_resp.usage.output_tokens = 5
        mock_client.messages.create.return_value = mock_resp

        result = provider.complete("", "Say hello", "claude-sonnet-4-6", 0.7, 256)

        assert isinstance(result, ProviderResponse)
        assert result.content == "Hello!"
        assert result.provider == "anthropic"
        assert result.input_tokens == 10
        assert result.output_tokens == 5
        assert result.total_tokens == 15

    def test_complete_with_system_prompt(self):
        provider, _, mock_client = _make_anthropic()
        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="answer")]
        mock_resp.model = "claude-sonnet-4-6"
        mock_resp.usage.input_tokens = 20
        mock_resp.usage.output_tokens = 3
        mock_client.messages.create.return_value = mock_resp

        provider.complete("You are helpful.", "Hello", "claude-sonnet-4-6", 0.5, 512)

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["system"] == "You are helpful."

    def test_complete_empty_content_returns_empty_string(self):
        provider, _, mock_client = _make_anthropic()
        mock_resp = MagicMock()
        mock_resp.content = []
        mock_resp.model = "claude-sonnet-4-6"
        mock_resp.usage.input_tokens = 5
        mock_resp.usage.output_tokens = 0
        mock_client.messages.create.return_value = mock_resp

        result = provider.complete("", "Hi", "claude-sonnet-4-6", 0.7, 128)
        assert result.content == ""

    def test_complete_uses_default_model_when_empty(self):
        provider, _, mock_client = _make_anthropic()
        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="ok")]
        mock_resp.model = "claude-sonnet-4-6"
        mock_resp.usage.input_tokens = 1
        mock_resp.usage.output_tokens = 1
        mock_client.messages.create.return_value = mock_resp

        provider.complete("", "Hi", "", 0.7, 128)  # empty model

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-sonnet-4-6"

    def test_complete_connection_error(self):
        provider, _, mock_client = _make_anthropic()
        mock_client.messages.create.side_effect = _ConnErr("timeout")
        with pytest.raises(ProviderError, match="Connection error"):
            provider.complete("", "Hi", "claude-sonnet-4-6", 0.7, 128)

    def test_complete_auth_error(self):
        provider, _, mock_client = _make_anthropic()
        mock_client.messages.create.side_effect = _AuthErr()
        with pytest.raises(ProviderError, match="authentication failed"):
            provider.complete("", "Hi", "claude-sonnet-4-6", 0.7, 128)

    def test_complete_rate_limit_error(self):
        provider, _, mock_client = _make_anthropic()
        mock_client.messages.create.side_effect = _RateErr()
        with pytest.raises(ProviderError, match="Rate limit"):
            provider.complete("", "Hi", "claude-sonnet-4-6", 0.7, 128)

    def test_complete_api_status_error(self):
        provider, _, mock_client = _make_anthropic()
        mock_client.messages.create.side_effect = _StatusErr(status_code=429, message="quota")
        with pytest.raises(ProviderError, match="API error 429"):
            provider.complete("", "Hi", "claude-sonnet-4-6", 0.7, 128)

    def test_stream_complete_yields_chunks(self):
        provider, _, mock_client = _make_anthropic()
        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__enter__ = MagicMock(return_value=mock_stream_ctx)
        mock_stream_ctx.__exit__ = MagicMock(return_value=False)
        mock_stream_ctx.text_stream = iter(["Hello", " world"])
        mock_client.messages.stream.return_value = mock_stream_ctx

        chunks = list(provider.stream_complete("", "Hi", "claude-sonnet-4-6", 0.7, 256))
        assert chunks == ["Hello", " world"]

    def test_stream_complete_auth_error(self):
        provider, _, mock_client = _make_anthropic()
        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__enter__.side_effect = _AuthErr()
        mock_stream_ctx.__exit__ = MagicMock(return_value=False)
        mock_client.messages.stream.return_value = mock_stream_ctx

        with pytest.raises(ProviderError, match="authentication failed"):
            list(provider.stream_complete("", "Hi", "claude-sonnet-4-6", 0.7, 256))

    def test_stream_complete_rate_limit_error(self):
        provider, _, mock_client = _make_anthropic()
        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__enter__.side_effect = _RateErr()
        mock_stream_ctx.__exit__ = MagicMock(return_value=False)
        mock_client.messages.stream.return_value = mock_stream_ctx

        with pytest.raises(ProviderError, match="rate limit"):
            list(provider.stream_complete("", "Hi", "claude-sonnet-4-6", 0.7, 256))


# ── OpenAIProvider ─────────────────────────────────────────────────────────────


def _make_openai(api_key: str = "sk-test") -> tuple:
    """Build an OpenAIProvider with a fully mocked SDK."""
    mock_sdk = MagicMock()
    mock_sdk.APIConnectionError = _ConnErr
    mock_sdk.AuthenticationError = _AuthErr
    mock_sdk.RateLimitError = _RateErr
    mock_sdk.APIStatusError = _StatusErr
    mock_client = MagicMock()
    mock_sdk.OpenAI.return_value = mock_client

    with patch.dict(sys.modules, {"openai": mock_sdk}):
        with patch.dict(os.environ, {"OPENAI_API_KEY": api_key}):
            from prompt_run.providers.openai import OpenAIProvider

            provider = OpenAIProvider()

    return provider, mock_sdk, mock_client


class TestOpenAIProvider:
    def test_missing_api_key_raises(self):
        mock_sdk = MagicMock()
        with patch.dict(sys.modules, {"openai": mock_sdk}):
            with patch.dict(os.environ, {}, clear=True):
                os.environ.pop("OPENAI_API_KEY", None)
                from prompt_run.providers.openai import OpenAIProvider

                with pytest.raises(ProviderError, match="OPENAI_API_KEY"):
                    OpenAIProvider()

    def test_default_model(self):
        provider, _, _ = _make_openai()
        assert provider.default_model() == "gpt-4o"

    def test_complete_returns_provider_response(self):
        provider, _, mock_client = _make_openai()
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = "GPT reply"
        mock_resp.model = "gpt-4o"
        mock_resp.usage.prompt_tokens = 15
        mock_resp.usage.completion_tokens = 8
        mock_resp.usage.total_tokens = 23
        mock_client.chat.completions.create.return_value = mock_resp

        result = provider.complete("", "Hello", "gpt-4o", 0.7, 512)

        assert isinstance(result, ProviderResponse)
        assert result.content == "GPT reply"
        assert result.provider == "openai"
        assert result.input_tokens == 15
        assert result.output_tokens == 8
        assert result.total_tokens == 23

    def test_complete_with_system_injects_system_message(self):
        provider, _, mock_client = _make_openai()
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = "ok"
        mock_resp.model = "gpt-4o"
        mock_resp.usage.prompt_tokens = 5
        mock_resp.usage.completion_tokens = 2
        mock_resp.usage.total_tokens = 7
        mock_client.chat.completions.create.return_value = mock_resp

        provider.complete("Be concise.", "Hello", "gpt-4o", 0.5, 128)

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        messages = call_kwargs["messages"]
        assert messages[0] == {"role": "system", "content": "Be concise."}
        assert messages[1] == {"role": "user", "content": "Hello"}

    def test_complete_uses_default_model_when_empty(self):
        provider, _, mock_client = _make_openai()
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = "ok"
        mock_resp.model = "gpt-4o"
        mock_resp.usage.prompt_tokens = 1
        mock_resp.usage.completion_tokens = 1
        mock_resp.usage.total_tokens = 2
        mock_client.chat.completions.create.return_value = mock_resp

        provider.complete("", "Hi", "", 0.7, 128)  # empty model

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4o"

    def test_complete_auth_error(self):
        provider, _, mock_client = _make_openai()
        mock_client.chat.completions.create.side_effect = _AuthErr()
        with pytest.raises(ProviderError, match="authentication failed"):
            provider.complete("", "Hi", "gpt-4o", 0.7, 128)

    def test_complete_rate_limit_error(self):
        provider, _, mock_client = _make_openai()
        mock_client.chat.completions.create.side_effect = _RateErr()
        with pytest.raises(ProviderError, match="rate limit"):
            provider.complete("", "Hi", "gpt-4o", 0.7, 128)

    def test_complete_connection_error(self):
        provider, _, mock_client = _make_openai()
        mock_client.chat.completions.create.side_effect = _ConnErr("refused")
        with pytest.raises(ProviderError, match="Connection error"):
            provider.complete("", "Hi", "gpt-4o", 0.7, 128)

    def test_complete_api_status_error(self):
        provider, _, mock_client = _make_openai()
        mock_client.chat.completions.create.side_effect = _StatusErr(
            status_code=503, message="unavailable"
        )
        with pytest.raises(ProviderError, match="API error 503"):
            provider.complete("", "Hi", "gpt-4o", 0.7, 128)

    def test_stream_complete_yields_chunks(self):
        provider, _, mock_client = _make_openai()
        chunk1 = MagicMock()
        chunk1.choices = [MagicMock()]
        chunk1.choices[0].delta.content = "Hello"
        chunk2 = MagicMock()
        chunk2.choices = [MagicMock()]
        chunk2.choices[0].delta.content = " world"
        mock_client.chat.completions.create.return_value = iter([chunk1, chunk2])

        chunks = list(provider.stream_complete("", "Hi", "gpt-4o", 0.7, 256))
        assert chunks == ["Hello", " world"]

    def test_stream_complete_skips_none_content(self):
        provider, _, mock_client = _make_openai()
        chunk1 = MagicMock()
        chunk1.choices = [MagicMock()]
        chunk1.choices[0].delta.content = None  # empty delta
        chunk2 = MagicMock()
        chunk2.choices = [MagicMock()]
        chunk2.choices[0].delta.content = "answer"
        mock_client.chat.completions.create.return_value = iter([chunk1, chunk2])

        chunks = list(provider.stream_complete("", "Hi", "gpt-4o", 0.7, 256))
        assert chunks == ["answer"]

    def test_stream_complete_auth_error(self):
        provider, _, mock_client = _make_openai()
        mock_client.chat.completions.create.side_effect = _AuthErr()
        with pytest.raises(ProviderError, match="authentication failed"):
            list(provider.stream_complete("", "Hi", "gpt-4o", 0.7, 256))


# ── OllamaProvider ─────────────────────────────────────────────────────────────


def _make_ollama():
    from prompt_run.providers.ollama import OllamaProvider

    return OllamaProvider()


def _mock_ollama_response(content: str, in_tok: int = 10, out_tok: int = 5) -> MagicMock:
    payload = json.dumps(
        {
            "message": {"content": content},
            "prompt_eval_count": in_tok,
            "eval_count": out_tok,
        }
    ).encode()
    mock_resp = MagicMock()
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.read.return_value = payload
    return mock_resp


class TestOllamaProvider:
    def test_default_model(self):
        provider = _make_ollama()
        assert provider.default_model() == "llama3"

    def test_complete_returns_provider_response(self):
        provider = _make_ollama()
        mock_resp = _mock_ollama_response("Ollama reply", in_tok=12, out_tok=6)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = provider.complete("", "Hello", "llama3", 0.7, 512)

        assert isinstance(result, ProviderResponse)
        assert result.content == "Ollama reply"
        assert result.provider == "ollama"
        assert result.input_tokens == 12
        assert result.output_tokens == 6
        assert result.total_tokens == 18

    def test_complete_with_system_message(self):
        provider = _make_ollama()
        mock_resp = _mock_ollama_response("ok")
        captured_payload = {}

        def fake_urlopen(req, timeout):
            captured_payload["data"] = json.loads(req.data)
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            provider.complete("Be brief.", "Hi", "llama3", 0.5, 128)

        messages = captured_payload["data"]["messages"]
        assert messages[0] == {"role": "system", "content": "Be brief."}
        assert messages[1] == {"role": "user", "content": "Hi"}

    def test_complete_uses_default_model_when_empty(self):
        provider = _make_ollama()
        mock_resp = _mock_ollama_response("ok")
        captured = {}

        def fake_urlopen(req, timeout):
            captured["data"] = json.loads(req.data)
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            provider.complete("", "Hi", "", 0.7, 128)

        assert captured["data"]["model"] == "llama3"

    def test_complete_url_error_raises_provider_error(self):
        provider = _make_ollama()
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
            with pytest.raises(ProviderError, match="Cannot connect to Ollama"):
                provider.complete("", "Hi", "llama3", 0.7, 128)

    def test_complete_invalid_json_raises_provider_error(self):
        provider = _make_ollama()
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = b"not-json"

        with patch("urllib.request.urlopen", return_value=mock_resp):
            with pytest.raises(ProviderError, match="Invalid JSON"):
                provider.complete("", "Hi", "llama3", 0.7, 128)

    def test_custom_base_url_from_env(self):
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": "http://myhost:9999"}):
            provider = _make_ollama()
        assert provider._base_url == "http://myhost:9999"

    def test_base_url_trailing_slash_stripped(self):
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": "http://myhost:9999/"}):
            provider = _make_ollama()
        assert not provider._base_url.endswith("/")
