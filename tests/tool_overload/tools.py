"""Load tool definitions for the tool-overload test."""

from pathlib import Path
from typing import Any

import yaml

DEFINITIONS_PATH = Path(__file__).parent / "data" / "definitions.yaml"


def load_all_tools() -> list[dict[str, Any]]:
    """Load all tool definitions from YAML."""
    with open(DEFINITIONS_PATH) as f:
        data = yaml.safe_load(f)

    tools = []
    for tool_def in data["tools"]:
        name = tool_def["name"]
        service = name.split("_")[0]
        tools.append(
            {
                "name": name,
                "description": tool_def["description"],
                "service": service,
                "parameters": tool_def.get("parameters", {}),
            }
        )
    return tools
