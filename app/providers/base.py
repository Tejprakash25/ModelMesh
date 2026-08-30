from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class CompletionResult:
    content: str
    prompt_tokens: int
    completion_tokens: int
    model: str
    provider: str


class ProviderError(Exception):
    pass


class Provider(ABC):
    name: str

    @abstractmethod
    async def complete(self, model: str, messages: list[ChatMessage]) -> CompletionResult:
        pass
