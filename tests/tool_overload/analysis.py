"""Tool-overload test analysis and summary output."""

import pandas as pd
from rich.console import Console
from rich.table import Table

from bench.analysis import MODE_LABELS

console = Console()


def print_summary(df: pd.DataFrame) -> None:
    """Print summary tables to the console."""
    has_modes = df["mode"].nunique() > 1
    has_cost = "cost_usd" in df.columns and df["cost_usd"].sum() > 0

    table = Table(title="Accuracy by Tool Count")
    if has_modes:
        table.add_column("Mode")
    table.add_column("Provider")
    table.add_column("Tools")
    table.add_column("Accuracy %", justify="right")
    table.add_column("Cross-Svc Error %", justify="right")
    table.add_column("Avg Latency (ms)", justify="right")
    table.add_column("Avg Tokens", justify="right")
    if has_cost:
        table.add_column("Cost", justify="right")

    for mode in sorted(df["mode"].unique()):
        mdf = df[df["mode"] == mode]
        for provider in sorted(mdf["provider"].unique()):
            pdf = mdf[mdf["provider"] == provider]
            for num_tools in sorted(pdf["num_tools"].unique()):
                tdf = pdf[pdf["num_tools"] == num_tools]
                acc = tdf["correct"].mean() * 100
                cross_svc = tdf["cross_service_error"].mean() * 100
                latency = tdf["latency_ms"].mean()
                tokens = (tdf["input_tokens"] + tdf["output_tokens"]).mean()

                row = []
                if has_modes:
                    row.append(MODE_LABELS.get(mode, mode))
                row.extend(
                    [
                        provider,
                        str(num_tools),
                        f"{acc:.1f}",
                        f"{cross_svc:.1f}",
                        f"{latency:.0f}",
                        f"{tokens:.0f}",
                    ]
                )
                if has_cost:
                    cost = tdf["cost_usd"].sum()
                    row.append(f"${cost:.4f}")
                table.add_row(*row)

    console.print(table)

    # Total cost across all results
    if has_cost:
        total = df["cost_usd"].sum()
        console.print(f"\n  Total cost: [green]${total:.4f}[/green]")

    if has_modes:
        comp_table = Table(title="Disclosure Mode Comparison")
        comp_table.add_column("Provider")
        comp_table.add_column("Mode")
        comp_table.add_column("Avg Tools")
        comp_table.add_column("Accuracy %", justify="right")
        comp_table.add_column("Cross-Svc Error %", justify="right")
        comp_table.add_column("Avg Latency (ms)", justify="right")
        comp_table.add_column("Avg Input Tokens", justify="right")
        if has_cost:
            comp_table.add_column("Cost", justify="right")

        for provider in sorted(df["provider"].unique()):
            pdf = df[df["provider"] == provider]
            for mode in sorted(pdf["mode"].unique()):
                mdf = pdf[pdf["mode"] == mode]
                row = [
                    provider,
                    MODE_LABELS.get(mode, mode),
                    f"{mdf['num_tools'].mean():.0f}",
                    f"{mdf['correct'].mean() * 100:.1f}",
                    f"{mdf['cross_service_error'].mean() * 100:.1f}",
                    f"{mdf['latency_ms'].mean():.0f}",
                    f"{mdf['input_tokens'].mean():.0f}",
                ]
                if has_cost:
                    row.append(f"${mdf['cost_usd'].sum():.4f}")
                comp_table.add_row(*row)

        console.print(comp_table)
