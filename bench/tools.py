"""Shared tool schema converters for LLM providers."""

from typing import Any


def to_openai_schema(tool: dict[str, Any]) -> dict[str, Any]:
    """Convert a tool definition to OpenAI function-calling schema."""
    properties = {}
    required = []
    for param_name, param_def in tool["parameters"].items():
        properties[param_name] = {
            "type": param_def.get("type", "string"),
            "description": param_def.get("description", ""),
        }
        if param_def.get("required", False):
            required.append(param_name)

    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


def to_anthropic_schema(tool: dict[str, Any]) -> dict[str, Any]:
    """Convert a tool definition to Anthropic tool-use schema."""
    properties = {}
    required = []
    for param_name, param_def in tool["parameters"].items():
        properties[param_name] = {
            "type": param_def.get("type", "string"),
            "description": param_def.get("description", ""),
        }
        if param_def.get("required", False):
            required.append(param_name)

    return {
        "name": tool["name"],
        "description": tool["description"],
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
    }


def to_gemini_schema(tool: dict[str, Any]) -> dict[str, Any]:
    """Convert a tool definition to Gemini function-calling schema."""
    properties = {}
    required = []
    for param_name, param_def in tool["parameters"].items():
        type_map = {"string": "STRING", "integer": "INTEGER", "boolean": "BOOLEAN"}
        properties[param_name] = {
            "type": type_map.get(param_def.get("type", "string"), "STRING"),
            "description": param_def.get("description", ""),
        }
        if param_def.get("required", False):
            required.append(param_name)

    schema = {
        "name": tool["name"],
        "description": tool["description"],
        "parameters": {
            "type": "OBJECT",
            "properties": properties,
        },
    }
    if required:
        schema["parameters"]["required"] = required
    return schema
