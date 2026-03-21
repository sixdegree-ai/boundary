"""Tool Overload test plugin. Measures LLM tool-calling accuracy vs toolset size."""

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()

RESULTS_DIR = Path(__file__).parent.parent.parent / "results" / "tool_overload"


class ToolOverloadPlugin:
    name = "tool-overload"
    description = "LLM tool-calling accuracy vs toolset size, with late disclosure comparison"

    def register(self) -> click.Group:
        @click.group("tool-overload")
        def group():
            """Tool Overload: measure tool-calling accuracy at different toolset sizes."""
            pass

        group.add_command(_run)
        group.add_command(_analyze)
        group.add_command(_list_tools)
        group.add_command(_list_prompts)
        return group


# --- Commands ---


@click.command("run")
@click.option("-p", "--provider", multiple=True, default=["claude-sonnet"], help="Provider(s) to benchmark.")
@click.option("-t", "--tool-counts", default="5,10,20,40,60", help="Comma-separated tool counts (random mode only).")
@click.option("-n", "--trials", default=3, help="Trials per combo.")
@click.option("--seed", default=42, help="Random seed.")
@click.option("-c", "--categories", default="direct,ambiguous", help="Comma-separated prompt categories.")
@click.option("-l", "--limit", default=None, type=int, help="Limit number of prompts.")
@click.option(
    "-m",
    "--mode",
    type=click.Choice(["random", "all", "disclosed", "noisy"], case_sensitive=False),
    multiple=True,
    default=["random"],
    help="Disclosure mode(s). Specify multiple for comparison.",
)
def _run(provider, tool_counts, trials, seed, categories, limit, mode):
    """Run the tool overload benchmark."""
    from bench.providers import get_provider

    from .runner import BenchmarkConfig, run_benchmark, save_results

    for provider_name in provider:
        p = get_provider(provider_name)
        for m in mode:
            console.print(f"\n[bold blue]Starting: {provider_name} (mode={m})[/bold blue]")
            config = BenchmarkConfig(
                tool_counts=[int(x) for x in tool_counts.split(",")],
                trials_per_combo=trials,
                seed=seed,
                categories=[c.strip() for c in categories.split(",")],
                prompt_limit=limit,
                mode=m,
            )
            results = run_benchmark(p, config)
            save_results(results, p.name, mode=m, config=config)


@click.command("analyze")
@click.argument("result_files", nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option("--charts/--no-charts", default=True, help="Generate charts.")
@click.option("--plotly/--matplotlib", "use_plotly", default=True, help="Chart engine.")
@click.option("-o", "--output-dir", type=click.Path(path_type=Path), default=None)
def _analyze(result_files, charts, use_plotly, output_dir):
    """Analyze results and generate charts."""
    from bench.analysis import load_results

    from .analysis import print_summary

    if not result_files:
        result_files = sorted(RESULTS_DIR.glob("*.json"))
        if not result_files:
            console.print("[red]No results found. Run the benchmark first.[/red]")
            return

    console.print(f"Loading {len(result_files)} result file(s)...")
    df = load_results(list(result_files))
    print_summary(df)

    if charts:
        console.print("\n[bold]Generating charts...[/bold]")
        chart_dir = output_dir or RESULTS_DIR / "charts"
        if use_plotly:
            from bench.charts import generate_charts
        else:
            # Fallback: just print summary, no matplotlib in the new structure
            console.print("[dim]Matplotlib charts not available in new structure. Use --plotly.[/dim]")
            return
        generate_charts(df, chart_dir)


@click.command("list-tools")
def _list_tools():
    """List all available tools."""
    from .tools import load_all_tools

    tools = load_all_tools()
    table = Table(title=f"Available Tools ({len(tools)} total)")
    table.add_column("Service")
    table.add_column("Tool Name")
    table.add_column("Description", max_width=60)

    for t in sorted(tools, key=lambda x: (x["service"], x["name"])):
        table.add_row(t["service"], t["name"], t["description"])

    console.print(table)


@click.command("list-prompts")
def _list_prompts():
    """List all benchmark prompts."""
    from .prompts import load_prompts

    prompts = load_prompts()
    table = Table(title=f"Benchmark Prompts ({len(prompts)} total)")
    table.add_column("ID")
    table.add_column("Category")
    table.add_column("Expected Tool")
    table.add_column("Prompt", max_width=60)

    for p in prompts:
        table.add_row(p["id"], p["category"], p["expected_tool"], p["prompt"])

    console.print(table)


# This is what the framework discovers
plugin = ToolOverloadPlugin()
