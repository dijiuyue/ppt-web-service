"""
PPT Master Pipeline - LLM client wrapper.

Provides a unified async interface for OpenAI and Anthropic LLM backends
with configurable retries, timeout handling, and structured output parsing.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, AsyncIterator, Literal

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.pipeline.constants import (
    ANTHROPIC_MODELS,
    DEEPSEEK_MODELS,
    LLM_MAX_RETRIES,
    LLM_REQUEST_TIMEOUT,
    LLM_RETRY_DELAY_BASE,
    OPENAI_MODELS,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Provider-specific imports (soft-fail if unavailable)
# ---------------------------------------------------------------------------
try:
    import openai

    HAS_OPENAI = True
except ImportError:  # pragma: no cover
    HAS_OPENAI = False
    openai = None  # type: ignore[assignment]

try:
    import anthropic

    HAS_ANTHROPIC = True
except ImportError:  # pragma: no cover
    HAS_ANTHROPIC = False
    anthropic = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------
class LLMError(Exception):
    """Base exception for LLM-related errors."""


class LLMProviderError(LLMError):
    """Raised when the LLM provider returns an error."""


class LLMRateLimitError(LLMProviderError):
    """Raised when rate-limited by the LLM provider."""


class LLMTimeoutError(LLMError):
    """Raised when an LLM request times out."""


class LLMContentError(LLMError):
    """Raised when the LLM response cannot be parsed."""


# ---------------------------------------------------------------------------
# LLM Client
# ---------------------------------------------------------------------------
class LLMClient:
    """
    Unified async LLM client supporting OpenAI and Anthropic backends.

    Usage::

        client = LLMClient(provider="openai", model="gpt-4o")
        response = await client.chat_completion(
            system_prompt="You are a helpful assistant.",
            user_prompt="Hello!",
        )
    """

    def __init__(
        self,
        provider: Literal["openai", "anthropic"] = "openai",
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int | None = None,
    ) -> None:
        self.provider = provider.lower()
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout or LLM_REQUEST_TIMEOUT
        self._api_key = api_key
        self._base_url = base_url

        # Resolve model
        self.model = model or self._default_model()
        self._validate_model()

        # Initialize provider client
        self._client: Any = None
        self._init_client()

    # -- Internal helpers --------------------------------------------------

    def _default_model(self) -> str:
        if self.provider == "openai":
            return "gpt-4o"
        if self.provider == "deepseek":
            return "deepseek-v4-pro"
        return "claude-3-5-sonnet-latest"

    def _validate_model(self) -> None:
        if self.provider == "openai" and self.model not in OPENAI_MODELS:
            logger.warning(
                "Model %s not in known OpenAI models %s; proceeding anyway",
                self.model,
                OPENAI_MODELS,
            )
        elif self.provider == "deepseek" and self.model not in DEEPSEEK_MODELS:
            logger.warning(
                "Model %s not in known DeepSeek models %s; proceeding anyway",
                self.model,
                DEEPSEEK_MODELS,
            )
        elif self.provider == "anthropic" and self.model not in ANTHROPIC_MODELS:
            logger.warning(
                "Model %s not in known Anthropic models %s; proceeding anyway",
                self.model,
                ANTHROPIC_MODELS,
            )

    def _init_client(self) -> None:
        if self.provider in ("openai", "deepseek"):
            if not HAS_OPENAI:
                raise LLMError(
                    "OpenAI package not installed. "
                    "Run: pip install openai"
                )
            api_key = self._api_key or os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise LLMError("OPENAI_API_KEY not provided")
            client_kwargs: dict[str, Any] = {"api_key": api_key}
            base_url = self._base_url or os.environ.get("OPENAI_BASE_URL")
            if not base_url and self.provider == "deepseek":
                base_url = "https://api.deepseek.com"
            if base_url:
                client_kwargs["base_url"] = base_url
            self._client = openai.AsyncOpenAI(**client_kwargs)

        elif self.provider == "anthropic":
            if not HAS_ANTHROPIC:
                raise LLMError(
                    "Anthropic package not installed. "
                    "Run: pip install anthropic"
                )
            api_key = self._api_key or os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise LLMError("ANTHROPIC_API_KEY not provided")
            client_kwargs = {"api_key": api_key}
            base_url = self._base_url or os.environ.get("ANTHROPIC_BASE_URL")
            if base_url:
                client_kwargs["base_url"] = base_url
            self._client = anthropic.AsyncAnthropic(**client_kwargs)

        else:
            raise LLMError(f"Unsupported LLM provider: {self.provider}")

    # -- Retry decorator ----------------------------------------------------

    @staticmethod
    def _with_retry[**P, R](fn: Any) -> Any:
        """Apply tenacity retry to an async function."""
        return retry(
            stop=stop_after_attempt(LLM_MAX_RETRIES),
            wait=wait_exponential(
                multiplier=LLM_RETRY_DELAY_BASE,
                min=LLM_RETRY_DELAY_BASE,
                max=60,
            ),
            retry=retry_if_exception_type(
                (LLMProviderError, LLMRateLimitError, LLMTimeoutError, httpx.HTTPError)
            ),
            reraise=True,
        )(fn)

    # -- Public API --------------------------------------------------------

    async def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """
        Send a chat completion request and return the text content.

        Args:
            system_prompt: The system/role prompt.
            user_prompt: The user message.
            temperature: Override the default temperature.
            max_tokens: Override the default max_tokens.

        Returns:
            The LLM response text.

        Raises:
            LLMError: On failure after all retries.
        """
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens if max_tokens is not None else self.max_tokens

        if self.provider == "openai":
            return await self._chat_openai(system_prompt, user_prompt, temp, tokens)
        else:
            return await self._chat_anthropic(system_prompt, user_prompt, temp, tokens)

    async def chat_completion_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Stream a chat completion response token by token."""
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens if max_tokens is not None else self.max_tokens

        if self.provider == "openai":
            async for chunk in self._stream_openai(system_prompt, user_prompt, temp, tokens):
                yield chunk
        else:
            async for chunk in self._stream_anthropic(system_prompt, user_prompt, temp, tokens):
                yield chunk

    async def chat_completion_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """
        Send a chat completion and parse the response as JSON.

        Returns:
            Parsed JSON dict.

        Raises:
            LLMContentError: If response is not valid JSON.
        """
        raw = await self.chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        try:
            return self._parse_json_response(raw)
        except LLMContentError:
            logger.warning("JSON parsing failed, retrying with fix-prompt")
            retry_prompt = (
                user_prompt
                + "\n\nCRITICAL: Your previous response was not valid JSON. "
                + "Output ONLY valid, complete JSON. No markdown. No truncation."
            )
            raw2 = await self.chat_completion(
                system_prompt=system_prompt,
                user_prompt=retry_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return self._parse_json_response(raw2)

    def _parse_json_response(self, raw: str) -> dict[str, Any]:
        """Parse JSON from LLM response, with repair attempts."""
        cleaned = raw.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            repaired = self._repair_truncated_json(cleaned)
            if repaired is not None:
                logger.warning("JSON repaired after truncation")
                return repaired
            raise LLMContentError(
                f"Invalid JSON response: {cleaned[:200]}"
            ) from None

    @staticmethod
    def _repair_truncated_json(text: str) -> dict[str, Any] | None:
        """Attempt to repair truncated JSON by closing unclosed structures."""
        open_braces = text.count("{") - text.count("}")
        open_brackets = text.count("[") - text.count("]")

        if open_braces > 0:
            # Try closing unclosed string
            if text.rstrip().endswith('"'):
                pass
            elif '"' in text:
                in_string = False
                for ch in text:
                    if ch == '"':
                        in_string = not in_string
                if in_string:
                    text = text + '"'

            text = text.rstrip().rstrip(",")
            text += "]" * open_brackets
            text += "}" * open_braces
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
        return None

    # -- Provider-specific implementations ---------------------------------

    @retry(
        stop=stop_after_attempt(LLM_MAX_RETRIES),
        wait=wait_exponential(multiplier=LLM_RETRY_DELAY_BASE, min=2, max=60),
        retry=retry_if_exception_type(
            (LLMProviderError, LLMRateLimitError, LLMTimeoutError, httpx.HTTPError)
        ),
        reraise=True,
    )
    async def _chat_openai(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=self.timeout,
            )
            content = response.choices[0].message.content
            if content is None:
                raise LLMContentError("OpenAI returned empty content")
            return content

        except openai.RateLimitError as exc:
            raise LLMRateLimitError(f"OpenAI rate limit: {exc}") from exc
        except openai.APITimeoutError as exc:
            raise LLMTimeoutError(f"OpenAI timeout: {exc}") from exc
        except openai.APIError as exc:
            raise LLMProviderError(f"OpenAI API error: {exc}") from exc

    @retry(
        stop=stop_after_attempt(LLM_MAX_RETRIES),
        wait=wait_exponential(multiplier=LLM_RETRY_DELAY_BASE, min=2, max=60),
        retry=retry_if_exception_type(
            (LLMProviderError, LLMRateLimitError, LLMTimeoutError, httpx.HTTPError)
        ),
        reraise=True,
    )
    async def _chat_anthropic(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        try:
            response = await self._client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=self.timeout,
            )
            content_blocks = response.content
            if not content_blocks:
                raise LLMContentError("Anthropic returned empty content")
            # Anthropic returns a list of content blocks; extract text
            text_parts: list[str] = []
            for block in content_blocks:
                if hasattr(block, "text"):
                    text_parts.append(block.text)
                elif isinstance(block, dict) and "text" in block:
                    text_parts.append(block["text"])
            return "".join(text_parts)

        except anthropic.RateLimitError as exc:
            raise LLMRateLimitError(f"Anthropic rate limit: {exc}") from exc
        except anthropic.APITimeoutError as exc:
            raise LLMTimeoutError(f"Anthropic timeout: {exc}") from exc
        except anthropic.APIError as exc:
            raise LLMProviderError(f"Anthropic API error: {exc}") from exc

    async def _stream_openai(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        try:
            stream = await self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=self.timeout,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta

        except openai.RateLimitError as exc:
            raise LLMRateLimitError(f"OpenAI rate limit: {exc}") from exc
        except openai.APITimeoutError as exc:
            raise LLMTimeoutError(f"OpenAI timeout: {exc}") from exc
        except openai.APIError as exc:
            raise LLMProviderError(f"OpenAI API error: {exc}") from exc

    async def _stream_anthropic(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        try:
            async with self._client.messages.stream(
                model=self.model,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=self.timeout,
            ) as stream:
                async for text in stream.text_stream:
                    if text:
                        yield text

        except anthropic.RateLimitError as exc:
            raise LLMRateLimitError(f"Anthropic rate limit: {exc}") from exc
        except anthropic.APITimeoutError as exc:
            raise LLMTimeoutError(f"Anthropic timeout: {exc}") from exc
        except anthropic.APIError as exc:
            raise LLMProviderError(f"Anthropic API error: {exc}") from exc

    # -- Helpers -----------------------------------------------------------

    @staticmethod
    def extract_json_from_markdown(text: str) -> str:
        """Extract JSON content from markdown code fences."""
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return cleaned.strip()

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client is not None:
            await self._client.close()

    async def __aenter__(self) -> "LLMClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
