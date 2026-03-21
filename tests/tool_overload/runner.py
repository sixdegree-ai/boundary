"""Benchmark runner. Varies toolset size and measures accuracy."""

import json
import random
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn

from bench.types import Provider

from .prompts import load_prompts
from .tools import load_all_tools

console = Console()

RESULTS_DIR = Path(__file__).parent.parent.parent / "results" / "tool_overload"

DISCLOSURE_MODES = ["random", "all", "disclosed", "noisy"]


@dataclass
class TrialResult:
    prompt_id: str
    prompt_text: str
    expected_tool: str
    expected_service: str
    category: str
    num_tools: int
    trial: int
    actual_tool: str | None
    correct: bool
    cross_service_error: bool
    latency_ms: float
    input_tokens: int
    output_tokens: int
    mode: str = "random"


@dataclass
class BenchmarkConfig:
    tool_counts: list[int] = field(default_factory=lambda: [5, 10, 20, 40, 60])
    trials_per_combo: int = 3
    seed: int = 42
    categories: list[str] = field(default_factory=lambda: ["direct", "ambiguous"])
    prompt_limit: int | None = None
    mode: str = "random"


def _get_tools_by_service(all_tools: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_service: dict[str, list[dict[str, Any]]] = {}
    for t in all_tools:
        by_service.setdefault(t["service"], []).append(t)
    return by_service


def _pick_tool_subset(
    all_tools: list[dict[str, Any]],
    must_include: str,
    count: int,
    rng: random.Random,
) -> list[dict[str, Any]]:
    must_tool = next(t for t in all_tools if t["name"] == must_include)
    others = [t for t in all_tools if t["name"] != must_include]

    same_prefix = must_include.split("_")[0]
    confusors = [t for t in others if t["name"].startswith(same_prefix)]
    non_confusors = [t for t in others if not t["name"].startswith(same_prefix)]

    n_remaining = count - 1
    selected = []

    if confusors:
        n_conf = min(len(confusors), max(1, n_remaining // 3))
        selected.extend(rng.sample(confusors, n_conf))
        n_remaining -= n_conf

    available = [t for t in non_confusors if t not in selected]
    n_fill = min(len(available), n_remaining)
    selected.extend(rng.sample(available, n_fill))

    selected.append(must_tool)
    rng.shuffle(selected)
    return selected


def _pick_disclosed_subset(
    all_tools: list[dict[str, Any]],
    must_include: str,
    rng: random.Random,
) -> list[dict[str, Any]]:
    by_service = _get_tools_by_service(all_tools)
    target_service = must_include.split("_")[0]
    subset = list(by_service.get(target_service, []))
    rng.shuffle(subset)
    return subset


def _pick_noisy_subset(
    all_tools: list[dict[str, Any]],
    must_include: str,
    rng: random.Random,
) -> list[dict[str, Any]]:
    by_service = _get_tools_by_service(all_tools)
    target_service = must_include.split("_")[0]
    other_services = [s for s in by_service if s != target_service]
    noise_service = rng.choice(other_services)

    subset = list(by_service.get(target_service, []))
    subset.extend(by_service[noise_service])
    rng.shuffle(subset)
    return subset


def _select_tools_for_run(
    mode: str,
    all_tools: list[dict[str, Any]],
    expected_tool: str,
    num_tools: int,
    rng: random.Random,
) -> list[dict[str, Any]]:
    if mode == "all":
        tools = list(all_tools)
        rng.shuffle(tools)
        return tools
    elif mode == "disclosed":
        return _pick_disclosed_subset(all_tools, expected_tool, rng)
    elif mode == "noisy":
        return _pick_noisy_subset(all_tools, expected_tool, rng)
    else:
        return _pick_tool_subset(all_tools, expected_tool, num_tools, rng)


def _is_cross_service_error(
    actual_tool: str | None,
    expected_tool: str,
    all_tools: list[dict[str, Any]],
) -> bool:
    if actual_tool is None or actual_tool == expected_tool:
        return False
    expected_svc = next((t["service"] for t in all_tools if t["name"] == expected_tool), None)
    actual_svc = next((t["service"] for t in all_tools if t["name"] == actual_tool), None)
    return expected_svc != actual_svc


def _get_service_from_tool(tool_name: str) -> str:
    return tool_name.split("_")[0]


def run_benchmark(
    provider: Provider,
    config: BenchmarkConfig | None = None,
) -> list[TrialResult]:
    if config is None:
        config = BenchmarkConfig()

    all_tools = load_all_tools()
    prompts = load_prompts()
    prompts = [p for p in prompts if p["category"] in config.categories]
    if config.prompt_limit:
        prompts = prompts[: config.prompt_limit]
    rng = random.Random(config.seed)

    total_tools = len(all_tools)
    mode = config.mode

    if mode in ("all", "disclosed", "noisy"):
        tool_counts_label = {
            "all": f"all ({total_tools})",
            "disclosed": "service-only (5-11)",
            "noisy": "service + noise (11-22)",
        }[mode]
        total_runs = len(prompts) * config.trials_per_combo
    else:
        tool_counts = [min(c, total_tools) for c in config.tool_counts]
        tool_counts_label = str(tool_counts)
        total_runs = len(prompts) * len(tool_counts) * config.trials_per_combo

    results: list[TrialResult] = []

    console.print("\n[bold]Tool Overload Benchmark[/bold]")
    console.print(f"  Provider: {provider.name}")
    console.print(f"  Mode: {mode}")
    console.print(f"  Prompts: {len(prompts)}")
    console.print(f"  Tool counts: {tool_counts_label}")
    console.print(f"  Trials per combo: {config.trials_per_combo}")
    console.print(f"  Total API calls: {total_runs}\n")

    if mode in ("all", "disclosed", "noisy"):
        all_runs = [(0, prompt_data, trial) for prompt_data in prompts for trial in range(config.trials_per_combo)]
    else:
        all_runs = [
            (num_tools, prompt_data, trial)
            for num_tools in tool_counts
            for prompt_data in prompts
            for trial in range(config.trials_per_combo)
        ]

    # Sort by tool count for prompt caching, shuffle within each bucket
    runs_by_count: dict[int, list] = {}
    for run in all_runs:
        runs_by_count.setdefault(run[0], []).append(run)
    ordered_runs = []
    for tc in sorted(runs_by_count.keys()):
        bucket = runs_by_count[tc]
        rng.shuffle(bucket)
        ordered_runs.extend(bucket)
    all_runs = ordered_runs

    run_seeds = {
        (num_tools, prompt_data["id"], trial): random.Random(
            config.seed + hash((num_tools, prompt_data["id"], trial)) % (2**31)
        ).randint(0, 2**32)
        for num_tools, prompt_data, trial in all_runs
    }

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Running benchmark", total=total_runs)

        for num_tools, prompt_data, trial in all_runs:
            trial_rng = random.Random(run_seeds[(num_tools, prompt_data["id"], trial)])

            tool_subset = _select_tools_for_run(mode, all_tools, prompt_data["expected_tool"], num_tools, trial_rng)
            actual_num_tools = len(tool_subset)

            desc_tools = actual_num_tools if mode != "random" else num_tools
            progress.update(
                task,
                description=f"[{mode}:{desc_tools} tools] {prompt_data['id']} t{trial + 1}",
            )

            expected_service = _get_service_from_tool(prompt_data["expected_tool"])

            try:
                result = provider.call(prompt_data["prompt"], tool_subset)
                actual = result.tool_name
                correct = actual == prompt_data["expected_tool"]
                cross_svc = _is_cross_service_error(actual, prompt_data["expected_tool"], all_tools)

                results.append(
                    TrialResult(
                        prompt_id=prompt_data["id"],
                        prompt_text=prompt_data["prompt"],
                        expected_tool=prompt_data["expected_tool"],
                        expected_service=expected_service,
                        category=prompt_data["category"],
                        num_tools=actual_num_tools,
                        trial=trial,
                        actual_tool=actual,
                        correct=correct,
                        cross_service_error=cross_svc,
                        latency_ms=result.latency_ms,
                        input_tokens=result.input_tokens,
                        output_tokens=result.output_tokens,
                        mode=mode,
                    )
                )
            except Exception as e:
                console.print(f"  [red]Error[/red] {prompt_data['id']}: {e}")
                results.append(
                    TrialResult(
                        prompt_id=prompt_data["id"],
                        prompt_text=prompt_data["prompt"],
                        expected_tool=prompt_data["expected_tool"],
                        expected_service=expected_service,
                        category=prompt_data["category"],
                        num_tools=actual_num_tools,
                        trial=trial,
                        actual_tool=None,
                        correct=False,
                        cross_service_error=False,
                        latency_ms=0,
                        input_tokens=0,
                        output_tokens=0,
                        mode=mode,
                    )
                )

            progress.advance(task)

    return results


def save_results(results: list[TrialResult], provider_name: str, mode: str = "random") -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_name = provider_name.replace("/", "_")
    filename = RESULTS_DIR / f"{safe_name}_{mode}_{timestamp}.json"

    data = {
        "provider": provider_name,
        "mode": mode,
        "timestamp": timestamp,
        "total_prompts": len(set(r.prompt_id for r in results)),
        "results": [asdict(r) for r in results],
    }

    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

    console.print(f"\n[green]Results saved to {filename}[/green]")
    return filename
