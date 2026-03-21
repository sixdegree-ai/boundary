"""Load benchmark prompts for the tool-overload test."""

from pathlib import Path
from typing import Any

import yaml

PROMPTS_PATH = Path(__file__).parent / "data" / "benchmark.yaml"


def load_prompts() -> list[dict[str, Any]]:
    """Load all benchmark prompts from YAML."""
    with open(PROMPTS_PATH) as f:
        data = yaml.safe_load(f)
    return data["prompts"]
