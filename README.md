# Boundary

Open-source agent context testing framework.

Boundary runs reproducible tests against LLM providers to measure how models behave under real-world agent conditions. Each test is self-contained with its own data, runner, and analysis.

## Tests

| Test | What it measures |
|------|-----------------|
| `tool-overload` | Tool-calling accuracy at different toolset sizes (5 to 60+ tools) |

More tests coming soon. See [Contributing a test](#contributing-a-test) below.

## Quick start

```bash
# Create a .env file with your API keys
cat > .env << 'EOF'
ANTHROPIC_API_KEY=sk-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
XAI_API_KEY=xai-...
EOF

# List available tests
uv run boundary list-tests

# Run the tool-overload test against Claude Sonnet
uv run boundary tool-overload run -p claude-sonnet

# Run against multiple models
uv run boundary tool-overload run -p claude-sonnet -p gpt-4o -p gemini-flash

# Analyze results and generate charts
uv run boundary tool-overload analyze
```

## Supported models

Use shortcuts or full model names:

```bash
uv run boundary list-providers
```

| Provider  | Prefix       | Examples                                |
|-----------|--------------|-----------------------------------------|
| Anthropic | `claude-`    | `claude-sonnet`, `claude-haiku`         |
| OpenAI    | `gpt-`, `o1` | `gpt-4o`, `gpt-4o-mini`                |
| xAI       | `grok-`      | `grok-3`, `grok-3-mini`                |
| Google    | `gemini-`    | `gemini-flash`, `gemini-pro`            |

## Tool Overload test

99 tool definitions from production agent systems across 11 services (GitHub, GitLab, Jira, Confluence, Kubernetes, AWS, Datadog, Slack, PagerDuty, Okta, Snyk). Tests how well LLMs pick the correct tool when the available toolset ranges from 5 to 99.

### What it measures

- **Tool selection accuracy** at increasing toolset sizes
- **Cross-service confusion** (GitHub vs GitLab, Kubernetes vs Docker, etc.)
- **Latency and token usage** scaling with toolset size
- **Direct vs ambiguous prompts** (clear requests vs context-dependent ones)

### Disclosure mode comparison

The test can compare tool selection accuracy across different disclosure strategies, validating that late tool disclosure (progressively revealing tools based on context) outperforms loading all tools upfront.

| Mode | Flag | Description |
|------|------|-------------|
| `random` | `-m random` | Random subset of N tools (default) |
| `all` | `-m all` | All 99 tools every time |
| `disclosed` | `-m disclosed` | Only tools from the target service (5-11 tools) |
| `noisy` | `-m noisy` | Target service + one random other service (11-22 tools) |

```bash
# Compare all disclosure modes for a single model
uv run boundary tool-overload run -p claude-sonnet -m all -m disclosed -m noisy

# Quick comparison (1 trial, limited prompts)
uv run boundary tool-overload run -p claude-sonnet -m all -m disclosed -n 1 -l 20

# Full cross-model comparison
uv run boundary tool-overload run -p claude-sonnet -p gpt-4o -m all -m disclosed -m noisy

# Disclosure charts auto-generate when multiple modes are present
uv run boundary tool-overload analyze
```

### Cost optimization

- `-n 1` for single trial (default: 3)
- `-l N` to limit number of prompts
- `-t` with fewer tool counts (e.g. `-t 5,20,60`)
- Anthropic prompt caching is enabled automatically
- Running cost is shown live in the progress bar so you can Ctrl+C if needed

### Rate limits

At larger tool counts (60+), each call sends thousands of input tokens. Make sure your API tier has sufficient tokens-per-minute (TPM) limits. Boundary retries automatically on 429 errors with backoff (5s, 15s, 30s), but sustained rate limiting will slow your run. Tips:

- OpenAI Tier 1 accounts may struggle at 60+ tools with multiple trials. Use `-n 1` or request a TPM increase
- Anthropic prompt caching helps significantly since tool schemas are cached across calls
- Start with `-l 10 -n 1` to estimate your rate before committing to a full run

### Charts

Boundary generates interactive Plotly charts (HTML + optional PNG):

**Scaling charts** (random mode):
- `hero_degradation` - accuracy curve across toolset sizes

**Disclosure comparison** (multi-mode):
- `hero_disclosure` - 2x2 grid: accuracy, cross-service confusion, tokens, latency

## Contributing a test

Each test lives in its own directory under `tests/`:

```
tests/
  your_test/
    __init__.py
    test.py          # Plugin registration (name, description, CLI commands)
    runner.py         # Test-specific runner logic
    data/             # Test data (prompts, schemas, etc.)
```

The framework auto-discovers any directory under `tests/` that contains a `test.py` with a `plugin` object. See `tests/tool_overload/test.py` for an example.

### Plugin interface

```python
class YourTestPlugin:
    name = "your-test"
    description = "What this test measures"

    def register(self) -> click.Group:
        # Return a click group with run, analyze, and any extra commands
        ...

plugin = YourTestPlugin()
```

## Project structure

```
boundary/
  bench/                    # Shared framework
    cli.py                  # CLI entry point, test discovery
    providers.py            # LLM provider adapters (Anthropic, OpenAI, xAI, Gemini)
    charts.py               # Plotly chart engine
    tools.py                # Tool schema converters
    types.py                # Shared types (Provider, ProviderResult, TestPlugin)
    analysis.py             # Shared analysis utilities
  tests/                    # Self-contained tests
    tool_overload/
      test.py               # Plugin registration
      runner.py             # Benchmark runner with disclosure modes
      analysis.py           # Test-specific analysis
      tools.py              # Tool definition loader
      prompts.py            # Prompt loader
      data/
        definitions.yaml    # 99 tool definitions across 11 services
        benchmark.yaml      # 113 prompts (90 direct + 23 ambiguous)
  results/                  # Output (gitignored)
    tool_overload/
      *.json
      charts/
```

## License

MIT
