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
    """List available model providers and shortcuts."""
    table = Table(title="Available Providers")
    table.add_column("Shortcut")
    table.add_column("Model ID")
    table.add_column("Provider")

    shortcuts = [
        ("claude-sonnet", "claude-sonnet-4-20250514", "Anthropic"),
        ("claude-haiku", "claude-haiku-4-5-20251001", "Anthropic"),
        ("gpt-4o", "gpt-4o", "OpenAI"),
        ("gpt-4o-mini", "gpt-4o-mini", "OpenAI"),
        ("grok-3", "grok-3", "xAI"),
        ("grok-3-mini", "grok-3-mini", "xAI"),
        ("gemini-flash", "gemini-2.5-flash", "Google"),
        ("gemini-pro", "gemini-2.5-pro", "Google"),
    ]

    for shortcut, model_id, provider in shortcuts:
        table.add_row(shortcut, model_id, provider)

    console.print(table)
    console.print("\n[dim]You can also use full model names directly:[/dim]")
    console.print("  [cyan]claude-*[/cyan]  -> Anthropic")
    console.print("  [cyan]gpt-*[/cyan]     -> OpenAI")
    console.print("  [cyan]grok-*[/cyan]    -> xAI")
    console.print("  [cyan]gemini-*[/cyan]  -> Google")


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
