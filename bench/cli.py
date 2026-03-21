"""Boundary CLI. Auto-discovers tests from the tests/ directory."""

import importlib.util
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

console = Console()

TESTS_DIR = Path(__file__).parent.parent / "tests"


def discover_tests() -> dict[str, object]:
    """Scan tests/ for plugins. Each subdir with a test.py is a test."""
    plugins = {}
    if not TESTS_DIR.exists():
        return plugins
    for test_dir in sorted(TESTS_DIR.iterdir()):
        test_module = test_dir / "test.py"
        if test_dir.is_dir() and test_module.exists():
            spec = importlib.util.spec_from_file_location(f"tests.{test_dir.name}.test", test_module)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "plugin"):
                p = mod.plugin
                plugins[p.name] = p
    return plugins


@click.group()
@click.option(
    "--env-file",
    "-e",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to .env file (default: .env in current directory)",
)
def cli(env_file):
    """Boundary: agent context testing framework."""
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()


@cli.command("list-providers")
def list_providers():
    """List available models and shortcuts."""
    from bench.pricing import _load_models

    # Group by provider for readability
    by_provider: dict[str, list] = {}
    for m in _load_models():
        by_provider.setdefault(m["provider"], []).append(m)

    for provider, models in by_provider.items():
        console.print(f"\n  [bold]{provider}[/bold]")
        for m in models:
            aliases = m.get("aliases", [])
            p = m.get("pricing", {})
            alias_str = f" [dim]({', '.join(aliases)})[/dim]" if aliases else ""
            console.print(
                f"    {m['id']}{alias_str}"
                f"  [green]${p.get('input', 0):.2f}[/green] in"
                f" / [green]${p.get('output', 0):.2f}[/green] out per MTok"
            )

    console.print()
    console.print(
        "\n[bold yellow]WARNING:[/bold yellow] Pricing shown is approximate and may be outdated. "
        "Always verify current pricing at your provider's pricing page before running large benchmarks. "
        "To update pricing, edit bench/models.yaml."
    )


@cli.command("list-tests")
def list_tests():
    """List available tests."""
    plugins = discover_tests()
    if not plugins:
        console.print("[red]No tests found.[/red]")
        return

    table = Table(title="Available Tests")
    table.add_column("Name")
    table.add_column("Description")
    for p in plugins.values():
        table.add_row(p.name, p.description)
    console.print(table)


# Register discovered test plugins as subcommands
def _register_tests():
    for plugin in discover_tests().values():
        group = plugin.register()
        cli.add_command(group, plugin.name)


_register_tests()
