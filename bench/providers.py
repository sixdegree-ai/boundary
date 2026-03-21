"""LLM provider adapters."""

import time
from typing import Any

from .tools import to_anthropic_schema, to_gemini_schema, to_openai_schema
from .types import Provider, ProviderResult

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful assistant with access to various tools. "
    "When the user asks you to perform an action, call the most appropriate tool. "
    "Always call exactly one tool per request."
)


class AnthropicProvider(Provider):
    def __init__(self, model: str = "claude-sonnet-4-20250514", system_prompt: str | None = None):
        import anthropic

        self.client = anthropic.Anthropic()
        self.model = model
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        self._cached_tools: list[dict[str, Any]] | None = None
        self._cached_schemas: list[dict[str, Any]] | None = None

    @property
    def name(self) -> str:
        return f"anthropic/{self.model}"

    def call(self, prompt: str, tools: list[dict[str, Any]]) -> ProviderResult:
        tool_names = [t["name"] for t in tools]
        cached_names = [t["name"] for t in self._cached_tools] if self._cached_tools else []

        if tool_names == cached_names and self._cached_schemas:
            schemas = self._cached_schemas
        else:
            schemas = [to_anthropic_schema(t) for t in tools]
            if schemas:
                schemas[-1] = {**schemas[-1], "cache_control": {"type": "ephemeral"}}
            self._cached_tools = tools
            self._cached_schemas = schemas

        start = time.monotonic()
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=[{"type": "text", "text": self.system_prompt, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": prompt}],
            tools=schemas,
            tool_choice={"type": "any"},
        )
        latency = (time.monotonic() - start) * 1000

        tool_name = None
        tool_args = None
        for block in response.content:
            if block.type == "tool_use":
                tool_name = block.name
                tool_args = block.input
                break

        input_tokens = response.usage.input_tokens
        cache_read = getattr(response.usage, "cache_read_input_tokens", 0) or 0
        cache_creation = getattr(response.usage, "cache_creation_input_tokens", 0) or 0

        return ProviderResult(
            tool_name=tool_name,
            tool_args=tool_args,
            latency_ms=latency,
            input_tokens=input_tokens,
            output_tokens=response.usage.output_tokens,
            raw_response={"cache_read": cache_read, "cache_creation": cache_creation},
        )


class OpenAIProvider(Provider):
    def __init__(self, model: str = "gpt-4o", system_prompt: str | None = None):
        from openai import OpenAI

        self.client = OpenAI()
        self.model = model
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT

    @property
    def name(self) -> str:
        return f"openai/{self.model}"

    def call(self, prompt: str, tools: list[dict[str, Any]]) -> ProviderResult:
        schemas = [to_openai_schema(t) for t in tools]
        start = time.monotonic()
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ],
            tools=schemas,
            tool_choice="required",
        )
        latency = (time.monotonic() - start) * 1000

        tool_name = None
        tool_args = None
        if response.choices[0].message.tool_calls:
            tc = response.choices[0].message.tool_calls[0]
            tool_name = tc.function.name
            import json

            tool_args = json.loads(tc.function.arguments)

        return ProviderResult(
            tool_name=tool_name,
            tool_args=tool_args,
            latency_ms=latency,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
        )


class XAIProvider(Provider):
    """Grok models via xAI's OpenAI-compatible API."""

    def __init__(self, model: str = "grok-3", system_prompt: str | None = None):
        from openai import OpenAI

        self.client = OpenAI(
            api_key=__import__("os").environ.get("XAI_API_KEY"),
            base_url="https://api.x.ai/v1",
        )
        self.model = model
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT

    @property
    def name(self) -> str:
        return f"xai/{self.model}"

    def call(self, prompt: str, tools: list[dict[str, Any]]) -> ProviderResult:
        schemas = [to_openai_schema(t) for t in tools]
        start = time.monotonic()
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ],
            tools=schemas,
            tool_choice="required",
        )
        latency = (time.monotonic() - start) * 1000

        tool_name = None
        tool_args = None
        if response.choices[0].message.tool_calls:
            tc = response.choices[0].message.tool_calls[0]
            tool_name = tc.function.name
            import json

            tool_args = json.loads(tc.function.arguments)

        return ProviderResult(
            tool_name=tool_name,
            tool_args=tool_args,
            latency_ms=latency,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
        )


class GeminiProvider(Provider):
    def __init__(self, model: str = "gemini-2.5-flash", system_prompt: str | None = None):
        from google import genai

        self.client = genai.Client()
        self.model = model
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT

    @property
    def name(self) -> str:
        return f"gemini/{self.model}"

    def call(self, prompt: str, tools: list[dict[str, Any]]) -> ProviderResult:
        from google.genai import types

        function_declarations = [to_gemini_schema(t) for t in tools]
        gemini_tools = types.Tool(function_declarations=function_declarations)

        start = time.monotonic()
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=self.system_prompt,
                tools=[gemini_tools],
                tool_config=types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode="ANY",
                    )
                ),
            ),
        )
        latency = (time.monotonic() - start) * 1000

        tool_name = None
        tool_args = None
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    tool_name = part.function_call.name
                    tool_args = dict(part.function_call.args) if part.function_call.args else {}
                    break

        input_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
        output_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0

        return ProviderResult(
            tool_name=tool_name,
            tool_args=tool_args,
            latency_ms=latency,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )


def get_provider(name: str) -> Provider:
    """Get a provider by name or shortcut."""
    aliases = {
        "claude-sonnet": "claude-sonnet-4-20250514",
        "claude-haiku": "claude-haiku-4-5-20251001",
        "gemini-flash": "gemini-2.5-flash",
        "gemini-pro": "gemini-2.5-pro",
    }

    model = aliases.get(name, name)

    if model.startswith("claude-") or model.startswith("anthropic/"):
        model = model.removeprefix("anthropic/")
        return AnthropicProvider(model)
    elif model.startswith("gpt-") or model.startswith("o1") or model.startswith("openai/"):
        model = model.removeprefix("openai/")
        return OpenAIProvider(model)
    elif model.startswith("grok-") or model.startswith("xai/"):
        model = model.removeprefix("xai/")
        return XAIProvider(model)
    elif model.startswith("gemini-") or model.startswith("google/"):
        model = model.removeprefix("google/")
        return GeminiProvider(model)
    else:
        raise ValueError(
            f"Unknown provider for model: {name}. Model name should start with: claude-, gpt-, o1, grok-, or gemini-"
        )
