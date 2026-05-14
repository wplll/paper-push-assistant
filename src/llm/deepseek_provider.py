"""DeepSeek LLM provider using OpenAI-compatible API."""

import json
import logging
import re

from openai import OpenAI

from src.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from src.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek API provider using the OpenAI-compatible interface."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):
        self.api_key = api_key or DEEPSEEK_API_KEY
        self.base_url = base_url or DEEPSEEK_BASE_URL
        self.model = model or DEEPSEEK_MODEL
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        """Send a chat completion request with retry."""
        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.3,
                    max_tokens=4096,
                )
                content = response.choices[0].message.content or ""
                logger.debug("LLM response received (%d chars)", len(content))
                return content
            except Exception as e:
                last_error = e
                logger.warning("LLM call attempt %d failed: %s", attempt + 1, e)

        logger.error("All LLM attempts failed: %s", last_error)
        raise last_error  # type: ignore[misc]

    def chat_json(self, system_prompt: str, user_prompt: str) -> dict:
        """Send a chat request expecting JSON output.

        Tries to parse the response as JSON. If parsing fails,
        attempts to extract JSON from markdown code blocks.
        """
        raw = self.chat(system_prompt, user_prompt)
        return _extract_json(raw)


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM response, handling code fences and truncation."""
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from ```json ... ``` or ``` ... ```
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding first { to last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    # Return raw text as fallback
    logger.warning("Failed to parse JSON from LLM response, returning raw text")
    return {"raw_text": text, "parse_error": True}
