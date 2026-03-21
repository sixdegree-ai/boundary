"""Model pricing table. Costs per million tokens in USD."""

# fmt: off
# (input_per_mtok, output_per_mtok, cache_read_per_mtok, cache_write_per_mtok)
PRICING: dict[str, tuple[float, float, float, float]] = {
    # Anthropic
    "claude-sonnet-4-20250514":      (3.00,  15.00, 0.30, 3.75),
    "claude-opus-4-20250514":        (15.00, 75.00, 1.50, 18.75),
    "claude-haiku-4-5-20251001":     (0.80,  4.00,  0.08, 1.00),

    # OpenAI
    "gpt-4o":                        (2.50,  10.00, 0.0, 0.0),
    "gpt-4o-mini":                   (0.15,  0.60,  0.0, 0.0),
    "gpt-4-turbo":                   (10.00, 30.00, 0.0, 0.0),
    "o1":                            (15.00, 60.00, 0.0, 0.0),
    "o1-mini":                       (1.10,  4.40,  0.0, 0.0),
    "o1-preview":                    (15.00, 60.00, 0.0, 0.0),

    # xAI
    "grok-3":                        (3.00,  15.00, 0.0, 0.0),
    "grok-3-mini":                   (0.30,  0.50,  0.0, 0.0),
    "grok-4-fast-reasoning":         (3.00,  15.00, 0.0, 0.0),

    # Google
    "gemini-2.5-flash":              (0.15,  0.60,  0.0, 0.0),
    "gemini-2.5-pro":                (1.25,  10.00, 0.0, 0.0),
    "gemini-1.5-pro":                (1.25,  5.00,  0.0, 0.0),
}
# fmt: on


def get_pricing(model: str) -> tuple[float, float, float, float]:
    """Get (input, output, cache_read, cache_write) per MTok for a model.

    Returns zeros if model is unknown.
    """
    if model in PRICING:
        return PRICING[model]

    # Try prefix match for versioned model names
    for key in PRICING:
        if model.startswith(key) or key.startswith(model):
            return PRICING[key]

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

    # Tokens billed at cache rate are subtracted from regular input
    regular_input = input_tokens - cache_read_tokens - cache_creation_tokens
    regular_input = max(0, regular_input)

    cost = (
        (regular_input / 1_000_000) * inp
        + (output_tokens / 1_000_000) * out
        + (cache_read_tokens / 1_000_000) * cache_read
        + (cache_creation_tokens / 1_000_000) * cache_write
    )
    return cost
