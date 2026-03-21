"""Model pricing loaded from models.yaml."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

MODELS_PATH = Path(__file__).parent / "models.yaml"


@lru_cache
def _load_models() -> list[dict[str, Any]]:
    with open(MODELS_PATH) as f:
        return yaml.safe_load(f)["models"]


def get_pricing(model: str) -> tuple[float, float, float, float]:
    """Get (input, output, cache_read, cache_write) per MTok for a model."""
    for m in _load_models():
        if m["id"] == model:
            p = m["pricing"]
            return (p.get("input", 0), p.get("output", 0), p.get("cache_read", 0), p.get("cache_write", 0))

    # Prefix match for versioned names
    for m in _load_models():
        if model.startswith(m["id"]) or m["id"].startswith(model):
            p = m["pricing"]
            return (p.get("input", 0), p.get("output", 0), p.get("cache_read", 0), p.get("cache_write", 0))

    return (0.0, 0.0, 0.0, 0.0)


def calc_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_creation_tokens: int = 0,
) -> float:
    """Calculate cost in USD for a single API call."""
    inp, out, cache_read, cache_write = get_pricing(model)

    regular_input = max(0, input_tokens - cache_read_tokens - cache_creation_tokens)

    return (
        (regular_input / 1_000_000) * inp
        + (output_tokens / 1_000_000) * out
        + (cache_read_tokens / 1_000_000) * cache_read
        + (cache_creation_tokens / 1_000_000) * cache_write
    )
