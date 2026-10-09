from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

class LLMProvider(Protocol):

    def parse(self, system: str, user: str, response_model: type[T], context: dict | None = None) -> T:
        ...
