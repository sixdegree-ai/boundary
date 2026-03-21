"""Shared types for the framework."""

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable

import click


class ProviderResult:
    """Result from an LLM tool-call request."""

    def __init__(
        self,
        tool_name: str | None,
        tool_args: dict[str, Any] | None,
        latency_ms: float,
        input_tokens: int,
        output_tokens: int,
        raw_response: Any = None,
    ):
        self.tool_name = tool_name
        self.tool_args = tool_args
        self.latency_ms = latency_ms
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.raw_response = raw_response


class Provider(ABC):
    """Base class for LLM providers."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def call(self, prompt: str, tools: list[dict[str, Any]]) -> ProviderResult: ...


@runtime_checkable
class TestPlugin(Protocol):
    """Protocol that each test plugin must implement."""

    name: str
    description: str

    def register(self) -> click.Group:
        """Return a click group with run, analyze, and any extra commands."""
        ...
