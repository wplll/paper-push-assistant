"""Abstract base for LLM providers."""

from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    """Base class for LLM providers."""

    @abstractmethod
    def chat(self, system_prompt: str, user_prompt: str) -> str:
        """Send a chat request and return the response text."""
        ...

    @abstractmethod
    def chat_json(self, system_prompt: str, user_prompt: str) -> dict:
        """Send a chat request expecting JSON output, return parsed dict."""
        ...
