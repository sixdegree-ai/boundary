"""Hero charts for blog posts and social media. Dark theme."""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from rich.console import Console

console = Console()

# ---------------------------------------------------------------------------
# Dark palette
# ---------------------------------------------------------------------------
_BG = "#0d1117"  # GitHub-dark background
_SURFACE = "#161b22"  # card / plot area
_BORDER = "#30363d"  # subtle borders
_TEXT = "#e6edf3"  # primary text
_TEXT_MUTED = "#8b949e"  # secondary text
_GRID = "#21262d"  # gridlines, barely visible

_RED = "#f85149"
_ORANGE = "#d29922"
_GREEN = "#3fb950"
_BLUE = "#58a6ff"
_PURPLE = "#bc8cff"
_CYAN = "#39d2c0"
_PINK = "#f778ba"
_GRAY = "#484f58"

MODE_COLORS = {
    "all": _RED,
    "noisy": _ORANGE,
    "random": _GRAY,
    "disclosed": _GREEN,
}

_PROVIDER_PALETTE = [_BLUE, _ORANGE, _CYAN, _PINK, _PURPLE, _GREEN]

_FONT = "JetBrains Mono, SF Mono, Consolas, monospace"


def _save(fig: go.Figure, output_dir: Path, name: str, w: int = 1200, h: int = 700) -> None:
    fig.write_html(output_dir / f"{name}.html", include_plotlyjs="cdn")
    try:
        fig.write_image(output_dir / f"{name}.png", width=w, height=h, scale=2)
        console.print(f"  [green]Saved {name}.html + {name}.png[/green]")
    except Exception:
        console.print(f"  [green]Saved {name}.html[/green] [dim](PNG: run `plotly_get_chrome`)[/dim]")


def generate_charts(df: pd.DataFrame, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    df = df.copy()
    df["total_tokens"] = df["input_tokens"] + df["output_tokens"]

    modes = set(df["mode"].unique())

    if "random" in modes:
        _hero_degradation(df[df["mode"] == "random"].copy(), output_dir)

    if len(modes - {"random"}) > 0:
        _hero_disclosure(df.copy(), output_dir)

    console.print(f"\n[bold green]Charts saved to {output_dir}[/bold green]")


# ---------------------------------------------------------------------------
# CHART 1: "The Problem" - accuracy degrades with more tools
# ---------------------------------------------------------------------------


def _hero_degradation(df: pd.DataFrame, output_dir: Path) -> None:
    providers = sorted(df["provider"].unique())
    colors = {p: _PROVIDER_PALETTE[i % len(_PROVIDER_PALETTE)] for i, p in enumerate(providers)}

    acc = df.groupby(["provider", "num_tools"])["correct"].mean().reset_index()
    acc["pct"] = acc["correct"] * 100

    fig = go.Figure()

    # Zone bands
    fig.add_hrect(
        y0=95,
        y1=105,
        fillcolor=_GREEN,
        opacity=0.06,
        line_width=0,
        annotation_text="safe zone",
        annotation_position="top left",
        annotation=dict(font=dict(size=11, color=_GREEN, family=_FONT), opacity=0.6),
    )
    fig.add_hrect(
        y0=0,
        y1=80,
        fillcolor=_RED,
        opacity=0.04,
        line_width=0,
        annotation_text="danger zone",
        annotation_position="bottom left",
        annotation=dict(font=dict(size=11, color=_RED, family=_FONT), opacity=0.6),
    )

    for provider in providers:
        pdf = acc[acc["provider"] == provider].sort_values("num_tools")
        short_name = provider.split("/")[-1]
        c = colors[provider]

        # Gradient fill under the line
        fig.add_trace(
            go.Scatter(
                x=pdf["num_tools"],
                y=pdf["pct"],
                mode="none",
                fill="tozeroy",
                fillcolor=f"rgba({_hex_to_rgb(c)}, 0.08)",
                showlegend=False,
                hoverinfo="skip",
            )
        )

        # The line itself
        fig.add_trace(
            go.Scatter(
                x=pdf["num_tools"],
                y=pdf["pct"],
                name=short_name,
                mode="lines+markers+text",
                line=dict(color=c, width=3, shape="spline"),
                marker=dict(size=12, color=_SURFACE, line=dict(color=c, width=2.5)),
                text=[f"<b>{v:.0f}%</b>" for v in pdf["pct"]],
                textposition="top center",
                textfont=dict(size=13, color=c, family=_FONT),
            )
        )

    # Annotation arrow on worst drop
    if len(providers) > 0 and len(acc) > 1:
        worst = acc.loc[acc.groupby("provider")["pct"].idxmin()]
        worst_row = worst.sort_values("pct").iloc[0]
        fig.add_annotation(
            x=worst_row["num_tools"],
            y=worst_row["pct"] - 2,
            text=f"<b>{worst_row['pct']:.0f}%</b> with {int(worst_row['num_tools'])} tools",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=1.5,
            arrowcolor=_RED,
            ax=0,
            ay=40,
            font=dict(size=12, color=_RED, family=_FONT),
            bordercolor=_RED,
            borderwidth=1,
            borderpad=6,
            bgcolor=f"rgba({_hex_to_rgb(_RED)}, 0.1)",
        )

    fig.update_layout(
        title=dict(
            text=(
                f"<b>How Many Tools Is Too Many?</b>"
                f"<br><span style='font-size:13px;color:{_TEXT_MUTED}'>"
                f"Tool-calling accuracy across {len(providers)} model{'s' if len(providers) != 1 else ''} "
                f"with {int(acc['num_tools'].min())} to {int(acc['num_tools'].max())} tools"
                f"</span>"
            ),
            font=dict(size=22, color=_TEXT, family=_FONT),
            x=0.03,
            xanchor="left",
        ),
        font=dict(family=_FONT, size=12, color=_TEXT),
        plot_bgcolor=_SURFACE,
        paper_bgcolor=_BG,
        margin=dict(l=65, r=35, t=100, b=80),
        xaxis=dict(
            title=dict(text="TOOLS AVAILABLE TO LLM", font=dict(size=11, color=_TEXT_MUTED)),
            showgrid=False,
            zeroline=False,
            tickfont=dict(size=12, color=_TEXT_MUTED),
            linecolor=_BORDER,
            linewidth=1,
        ),
        yaxis=dict(
            title=dict(text="ACCURACY", font=dict(size=11, color=_TEXT_MUTED)),
            range=[0, 108],
            ticksuffix="%",
            showgrid=True,
            gridcolor=_GRID,
            gridwidth=1,
            zeroline=False,
            tickfont=dict(size=12, color=_TEXT_MUTED),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.17,
            xanchor="center",
            x=0.5,
            font=dict(size=12, color=_TEXT),
            bgcolor="rgba(0,0,0,0)",
        ),
        hoverlabel=dict(font_size=12, font_family=_FONT, bgcolor=_SURFACE, bordercolor=_BORDER),
    )

    _save(fig, output_dir, "hero_degradation", w=1100, h=650)


# ---------------------------------------------------------------------------
# CHART 2: "The Fix" - late disclosure side-by-side
# ---------------------------------------------------------------------------


def _hero_disclosure(df: pd.DataFrame, output_dir: Path) -> None:
    mode_sort = {"all": 0, "noisy": 1, "random": 2, "disclosed": 3}
    modes_present = sorted(df["mode"].unique(), key=lambda m: mode_sort.get(m, 99))

    agg = (
        df.groupby(["provider", "mode"])
        .agg(
            accuracy=("correct", "mean"),
            cross_svc=("cross_service_error", "mean"),
            avg_input=("input_tokens", "mean"),
            avg_latency=("latency_ms", "mean"),
        )
        .reset_index()
    )
    agg["accuracy"] *= 100
    agg["cross_svc"] *= 100

    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=["ACCURACY", "CROSS-SERVICE CONFUSION", "INPUT TOKENS / CALL", "LATENCY"],
        vertical_spacing=0.16,
        horizontal_spacing=0.10,
    )

    mode_labels = {"all": "All tools", "noisy": "Noisy", "random": "Random", "disclosed": "Disclosed"}

    metrics = [
        ("accuracy", "%", 1, 1, True),
        ("cross_svc", "%", 1, 2, False),
        ("avg_input", "tok", 2, 1, False),
        ("avg_latency", "ms", 2, 2, False),
    ]

    for metric, suffix, row, col, higher_is_better in metrics:
        for mode in modes_present:
            mdf = agg[agg["mode"] == mode].sort_values("provider")
            short_names = [p.split("/")[-1] for p in mdf["provider"]]
            vals = mdf[metric].values
            c = MODE_COLORS.get(mode, _GRAY)

            if suffix == "%":
                text = [f"<b>{v:.1f}</b>%" for v in vals]
            elif suffix == "tok":
                text = [f"<b>{v:,.0f}</b>" for v in vals]
            else:
                text = [f"<b>{v:,.0f}</b>ms" for v in vals]

            fig.add_trace(
                go.Bar(
                    x=short_names,
                    y=vals,
                    name=mode_labels.get(mode, mode),
                    marker=dict(color=c, line=dict(color=c, width=0), opacity=0.85),
                    text=text,
                    textposition="outside",
                    textfont=dict(size=11, color=c, family=_FONT),
                    showlegend=(row == 1 and col == 1),
                    legendgroup=mode,
                ),
                row=row,
                col=col,
            )

    # Style all subplots
    for r, c_idx in [(1, 1), (1, 2), (2, 1), (2, 2)]:
        fig.update_xaxes(
            row=r, col=c_idx, showgrid=False, tickfont=dict(size=10, color=_TEXT_MUTED), linecolor=_BORDER, linewidth=1
        )
        fig.update_yaxes(
            row=r,
            col=c_idx,
            showgrid=True,
            gridcolor=_GRID,
            gridwidth=1,
            zeroline=False,
            tickfont=dict(size=10, color=_TEXT_MUTED),
        )

    fig.update_yaxes(row=1, col=1, range=[0, 115], ticksuffix="%")
    fig.update_yaxes(row=1, col=2, ticksuffix="%")

    # Headline delta
    subtitle = ""
    if "all" in modes_present and "disclosed" in modes_present:
        all_acc = agg[agg["mode"] == "all"]["accuracy"].mean()
        disc_acc = agg[agg["mode"] == "disclosed"]["accuracy"].mean()
        all_tok = agg[agg["mode"] == "all"]["avg_input"].mean()
        disc_tok = agg[agg["mode"] == "disclosed"]["avg_input"].mean()
        delta = disc_acc - all_acc
        saving = (1 - disc_tok / all_tok) * 100 if all_tok > 0 else 0

        parts = []
        if delta > 0:
            parts.append(f'<span style="color:{_GREEN}">+{delta:.1f}% accuracy</span>')
        if saving > 0:
            parts.append(f'<span style="color:{_GREEN}">{saving:.0f}% fewer tokens</span>')
        if parts:
            joined = " &nbsp;/&nbsp; ".join(parts)
            subtitle = f"<br><span style='font-size:14px;color:{_TEXT_MUTED}'>Late disclosure: {joined}</span>"

    # Style subplot titles
    styled = []
    for a in fig.layout.annotations:
        a.update(font=dict(size=12, color=_TEXT_MUTED, family=_FONT))
        styled.append(a)

    fig.update_layout(
        title=dict(
            text=f"<b>Late Tool Disclosure</b>{subtitle}",
            font=dict(size=22, color=_TEXT, family=_FONT),
            x=0.03,
            xanchor="left",
        ),
        font=dict(family=_FONT, size=12, color=_TEXT),
        plot_bgcolor=_SURFACE,
        paper_bgcolor=_BG,
        margin=dict(l=60, r=30, t=110, b=60),
        barmode="group",
        bargap=0.25,
        bargroupgap=0.06,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.10,
            xanchor="center",
            x=0.5,
            font=dict(size=12, color=_TEXT),
            bgcolor="rgba(0,0,0,0)",
        ),
        annotations=styled,
        hoverlabel=dict(font_size=12, font_family=_FONT, bgcolor=_SURFACE, bordercolor=_BORDER),
    )

    _save(fig, output_dir, "hero_disclosure", w=1200, h=800)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hex_to_rgb(hex_color: str) -> str:
    """'#58a6ff' -> '88, 166, 255'"""
    h = hex_color.lstrip("#")
    return f"{int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}"
