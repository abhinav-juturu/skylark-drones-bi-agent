"""
Groq LLM Client with automatic fallback, streaming, and multi-model support.
"""

import logging
from typing import Any, Generator, Optional
from groq import Groq
from ..config import GROQ_API_KEY, DEFAULT_LLM_MODEL, FALLBACK_LLM_MODEL

logger = logging.getLogger(__name__)


class GroqLLMClient:
    """Client for generating completions using Groq's high-speed inference engine."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        fallback_model: Optional[str] = None,
    ):
        self.api_key = api_key or GROQ_API_KEY
        self.model = model or DEFAULT_LLM_MODEL
        self.fallback_model = fallback_model or FALLBACK_LLM_MODEL
        self.client = Groq(api_key=self.api_key) if self.api_key else None

    def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 2000,
    ) -> str:
        """Generate response with fallback handling."""
        if not self.client:
            raise ValueError("GROQ_API_KEY is not configured.")

        # Attempt primary model
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content or ""
            # Strip think tags if present (e.g. from reasoning models)
            if "<think>" in content and "</think>" in content:
                content = content.split("</think>")[-1].strip()
            return content

        except Exception as e:
            logger.warning("Primary model %s failed: %s. Attempting fallback %s...", self.model, e, self.fallback_model)
            try:
                response = self.client.chat.completions.create(
                    model=self.fallback_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                content = response.choices[0].message.content or ""
                if "<think>" in content and "</think>" in content:
                    content = content.split("</think>")[-1].strip()
                return content
            except Exception as fallback_err:
                logger.error("Fallback model %s also failed: %s", self.fallback_model, fallback_err)
                raise RuntimeError(f"LLM generation failed: {fallback_err}") from fallback_err

    def stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 2000,
    ) -> Generator[str, None, None]:
        """Stream response chunks in real-time."""
        if not self.client:
            raise ValueError("GROQ_API_KEY is not configured.")

        try:
            stream_resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            inside_think = False
            for chunk in stream_resp:
                delta = chunk.choices[0].delta.content or ""
                if "<think>" in delta:
                    inside_think = True
                    continue
                if "</think>" in delta:
                    inside_think = False
                    continue
                if not inside_think and delta:
                    yield delta

        except Exception as e:
            logger.warning("Streaming with %s failed: %s. Falling back to %s...", self.model, e, self.fallback_model)
            stream_resp = self.client.chat.completions.create(
                model=self.fallback_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            inside_think = False
            for chunk in stream_resp:
                delta = chunk.choices[0].delta.content or ""
                if "<think>" in delta:
                    inside_think = True
                    continue
                if "</think>" in delta:
                    inside_think = False
                    continue
                if not inside_think and delta:
                    yield delta
