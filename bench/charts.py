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


_generated_charts: list[tuple[str, str]] = []  # (filename, title)


def _save(fig: go.Figure, output_dir: Path, name: str, w: int = 1200, h: int = 700, title: str = "") -> None:
    fig.write_html(output_dir / f"{name}.html", include_plotlyjs="cdn")
    _generated_charts.append((f"{name}.html", title or name))
    try:
        fig.write_image(output_dir / f"{name}.png", width=w, height=h, scale=2)
        console.print(f"  [green]Saved {name}.html + {name}.png[/green]")
    except Exception:
        console.print(f"  [green]Saved {name}.html[/green] [dim](PNG: run `plotly_get_chrome`)[/dim]")


def _base_layout(**overrides) -> dict:
    layout = dict(
        font=dict(family=_FONT, size=12, color=_TEXT),
        plot_bgcolor=_SURFACE,
        paper_bgcolor=_BG,
        margin=dict(l=65, r=35, t=100, b=80),
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
    layout.update(overrides)
    return layout


def _provider_colors(providers: list[str]) -> dict[str, str]:
    return {p: _PROVIDER_PALETTE[i % len(_PROVIDER_PALETTE)] for i, p in enumerate(providers)}


def _short(provider: str) -> str:
    return provider.split("/")[-1]


def _xaxis(**overrides) -> dict:
    base = dict(
        showgrid=False,
        zeroline=False,
        tickfont=dict(size=12, color=_TEXT_MUTED),
        linecolor=_BORDER,
        linewidth=1,
    )
    base.update(overrides)
    return base


def _yaxis(**overrides) -> dict:
    base = dict(showgrid=True, gridcolor=_GRID, gridwidth=1, zeroline=False, tickfont=dict(size=12, color=_TEXT_MUTED))
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Chart generation entry point
# ---------------------------------------------------------------------------


def generate_charts(df: pd.DataFrame, output_dir: Path, run_id: str = "") -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _generated_charts.clear()

    df = df.copy()
    df["total_tokens"] = df["input_tokens"] + df["output_tokens"]
    has_cost = "cost_usd" in df.columns and df["cost_usd"].sum() > 0

    modes = set(df["mode"].unique())
    random_df = df[df["mode"] == "random"].copy() if "random" in modes else None

    if random_df is not None and len(random_df) > 0:
        _hero_degradation(random_df, output_dir)
        _chart_latency(random_df, output_dir)
        _chart_tokens(random_df, output_dir)
        if has_cost:
            _chart_cost(random_df, output_dir)
            _chart_cost_vs_accuracy(random_df, output_dir)
        _chart_service_heatmap(random_df, output_dir)
        _chart_error_breakdown(random_df, output_dir)

    if len(modes - {"random"}) > 0:
        _hero_disclosure(df, output_dir)

    # Build summary stats for the index
    providers = sorted(df["provider"].unique())
    total_calls = len(df)
    total_cost = df["cost_usd"].sum() if has_cost else 0
    modes_list = sorted(df["mode"].unique())
    tool_range = f"{int(df['num_tools'].min())}-{int(df['num_tools'].max())}"

    _build_index(output_dir, run_id, providers, total_calls, total_cost, modes_list, tool_range, df)
    console.print(f"\n[bold green]Charts saved to {output_dir}[/bold green]")


# ---------------------------------------------------------------------------
# CHART 1: "The Problem" - accuracy degrades with more tools
# ---------------------------------------------------------------------------


def _hero_degradation(df: pd.DataFrame, output_dir: Path) -> None:
    providers = sorted(df["provider"].unique())
    colors = _provider_colors(providers)

    acc = df.groupby(["provider", "num_tools"])["correct"].mean().reset_index()
    acc["pct"] = acc["correct"] * 100

    fig = go.Figure()

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
        c = colors[provider]

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
        fig.add_trace(
            go.Scatter(
                x=pdf["num_tools"],
                y=pdf["pct"],
                name=_short(provider),
                mode="lines+markers+text",
                line=dict(color=c, width=3, shape="spline"),
                marker=dict(size=12, color=_SURFACE, line=dict(color=c, width=2.5)),
                text=[f"<b>{v:.0f}%</b>" for v in pdf["pct"]],
                textposition="top center",
                textfont=dict(size=13, color=c, family=_FONT),
            )
        )

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
        **_base_layout(
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
            xaxis=_xaxis(title=dict(text="TOOLS AVAILABLE TO LLM", font=dict(size=11, color=_TEXT_MUTED))),
            yaxis=_yaxis(
                title=dict(text="ACCURACY", font=dict(size=11, color=_TEXT_MUTED)),
                range=[0, 108],
                ticksuffix="%",
            ),
        )
    )
    _save(fig, output_dir, "hero_degradation", w=1100, h=650, title="Accuracy vs Tool Count")


# ---------------------------------------------------------------------------
# CHART 2: Latency curve
# ---------------------------------------------------------------------------


def _chart_latency(df: pd.DataFrame, output_dir: Path) -> None:
    providers = sorted(df["provider"].unique())
    colors = _provider_colors(providers)

    lat = df.groupby(["provider", "num_tools"])["latency_ms"].agg(["mean", "std"]).reset_index()

    fig = go.Figure()
    for provider in providers:
        pdf = lat[lat["provider"] == provider].sort_values("num_tools")
        c = colors[provider]

        fig.add_trace(
            go.Scatter(
                x=pdf["num_tools"],
                y=pdf["mean"],
                name=_short(provider),
                mode="lines+markers+text",
                line=dict(color=c, width=3, shape="spline"),
                marker=dict(size=10, color=_SURFACE, line=dict(color=c, width=2.5)),
                text=[f"<b>{v / 1000:.1f}s</b>" for v in pdf["mean"]],
                textposition="top center",
                textfont=dict(size=11, color=c, family=_FONT),
            )
        )

    fig.update_layout(
        **_base_layout(
            title=dict(
                text="<b>Response Latency vs Toolset Size</b>",
                font=dict(size=22, color=_TEXT, family=_FONT),
                x=0.03,
                xanchor="left",
            ),
            xaxis=_xaxis(title=dict(text="TOOLS AVAILABLE TO LLM", font=dict(size=11, color=_TEXT_MUTED))),
            yaxis=_yaxis(title=dict(text="LATENCY (ms)", font=dict(size=11, color=_TEXT_MUTED))),
        )
    )
    _save(fig, output_dir, "latency", title="Response Latency")


# ---------------------------------------------------------------------------
# CHART 3: Token usage curve
# ---------------------------------------------------------------------------


def _chart_tokens(df: pd.DataFrame, output_dir: Path) -> None:
    providers = sorted(df["provider"].unique())
    colors = _provider_colors(providers)

    tok = df.groupby(["provider", "num_tools"])["input_tokens"].mean().reset_index()

    fig = go.Figure()
    for provider in providers:
        pdf = tok[tok["provider"] == provider].sort_values("num_tools")
        c = colors[provider]

        fig.add_trace(
            go.Scatter(
                x=pdf["num_tools"],
                y=pdf["input_tokens"],
                name=_short(provider),
                mode="lines+markers+text",
                line=dict(color=c, width=3, shape="spline"),
                marker=dict(size=10, color=_SURFACE, line=dict(color=c, width=2.5)),
                text=[f"<b>{v:,.0f}</b>" for v in pdf["input_tokens"]],
                textposition="top center",
                textfont=dict(size=11, color=c, family=_FONT),
            )
        )

    fig.update_layout(
        **_base_layout(
            title=dict(
                text="<b>Input Tokens per Call vs Toolset Size</b>",
                font=dict(size=22, color=_TEXT, family=_FONT),
                x=0.03,
                xanchor="left",
            ),
            xaxis=_xaxis(title=dict(text="TOOLS AVAILABLE TO LLM", font=dict(size=11, color=_TEXT_MUTED))),
            yaxis=_yaxis(title=dict(text="AVG INPUT TOKENS", font=dict(size=11, color=_TEXT_MUTED))),
        )
    )
    _save(fig, output_dir, "tokens", title="Token Usage")


# ---------------------------------------------------------------------------
# CHART 4: Cost per call
# ---------------------------------------------------------------------------


def _chart_cost(df: pd.DataFrame, output_dir: Path) -> None:
    providers = sorted(df["provider"].unique())
    colors = _provider_colors(providers)

    cost = df.groupby(["provider", "num_tools"])["cost_usd"].mean().reset_index()

    fig = go.Figure()
    for provider in providers:
        pdf = cost[cost["provider"] == provider].sort_values("num_tools")
        c = colors[provider]

        fig.add_trace(
            go.Scatter(
                x=pdf["num_tools"],
                y=pdf["cost_usd"],
                name=_short(provider),
                mode="lines+markers+text",
                line=dict(color=c, width=3, shape="spline"),
                marker=dict(size=10, color=_SURFACE, line=dict(color=c, width=2.5)),
                text=[f"<b>${v:.4f}</b>" for v in pdf["cost_usd"]],
                textposition="top center",
                textfont=dict(size=11, color=c, family=_FONT),
            )
        )

    fig.update_layout(
        **_base_layout(
            title=dict(
                text="<b>Cost per Call vs Toolset Size</b>",
                font=dict(size=22, color=_TEXT, family=_FONT),
                x=0.03,
                xanchor="left",
            ),
            xaxis=_xaxis(title=dict(text="TOOLS AVAILABLE TO LLM", font=dict(size=11, color=_TEXT_MUTED))),
            yaxis=_yaxis(
                title=dict(text="AVG COST PER CALL (USD)", font=dict(size=11, color=_TEXT_MUTED)), tickprefix="$"
            ),
        )
    )
    _save(fig, output_dir, "cost", title="Cost per Call")


# ---------------------------------------------------------------------------
# CHART 5: Cost vs accuracy tradeoff (scatter)
# ---------------------------------------------------------------------------


def _chart_cost_vs_accuracy(df: pd.DataFrame, output_dir: Path) -> None:
    providers = sorted(df["provider"].unique())
    colors = _provider_colors(providers)

    agg = (
        df.groupby(["provider", "num_tools"])
        .agg(
            accuracy=("correct", "mean"),
            cost=("cost_usd", "mean"),
        )
        .reset_index()
    )
    agg["accuracy"] *= 100

    fig = go.Figure()
    for provider in providers:
        pdf = agg[agg["provider"] == provider].sort_values("num_tools")
        c = colors[provider]

        fig.add_trace(
            go.Scatter(
                x=pdf["cost"],
                y=pdf["accuracy"],
                name=_short(provider),
                mode="markers+text",
                marker=dict(
                    size=pdf["num_tools"].values * 0.3 + 8,
                    color=c,
                    opacity=0.85,
                    line=dict(color=_TEXT, width=1),
                ),
                text=[f"{int(nt)}" for nt in pdf["num_tools"]],
                textposition="top center",
                textfont=dict(size=10, color=c, family=_FONT),
                hovertemplate=(
                    "<b>%{text} tools</b><br>Accuracy: %{y:.1f}%<br>Cost: $%{x:.4f}<br><extra>%{fullData.name}</extra>"
                ),
            )
        )

    fig.update_layout(
        **_base_layout(
            title=dict(
                text=(
                    "<b>Cost vs Accuracy Tradeoff</b>"
                    f"<br><span style='font-size:13px;color:{_TEXT_MUTED}'>Bubble size = tool count</span>"
                ),
                font=dict(size=22, color=_TEXT, family=_FONT),
                x=0.03,
                xanchor="left",
            ),
            xaxis=_xaxis(
                title=dict(text="AVG COST PER CALL (USD)", font=dict(size=11, color=_TEXT_MUTED)),
                tickprefix="$",
                showgrid=True,
                gridcolor=_GRID,
            ),
            yaxis=_yaxis(
                title=dict(text="ACCURACY", font=dict(size=11, color=_TEXT_MUTED)),
                range=[0, 108],
                ticksuffix="%",
            ),
        )
    )
    _save(fig, output_dir, "cost_vs_accuracy", title="Cost vs Accuracy Tradeoff")


# ---------------------------------------------------------------------------
# CHART 6: Per-service accuracy heatmap
# ---------------------------------------------------------------------------


def _chart_service_heatmap(df: pd.DataFrame, output_dir: Path) -> None:
    for provider in sorted(df["provider"].unique()):
        pdf = df[df["provider"] == provider]
        pivot = (
            pdf.groupby(["expected_service", "num_tools"])["correct"]
            .mean()
            .reset_index()
            .pivot(index="expected_service", columns="num_tools", values="correct")
        )
        pivot = pivot * 100

        fig = go.Figure(
            go.Heatmap(
                z=pivot.values,
                x=[str(c) for c in pivot.columns],
                y=pivot.index.tolist(),
                text=[[f"{v:.0f}" for v in row] for row in pivot.values],
                texttemplate="%{text}%",
                textfont=dict(size=12, family=_FONT),
                colorscale=[[0, _RED], [0.5, _ORANGE], [1, _GREEN]],
                zmin=0,
                zmax=100,
                colorbar=dict(
                    title=dict(text="Accuracy %", font=dict(color=_TEXT_MUTED)),
                    tickfont=dict(color=_TEXT_MUTED),
                    ticksuffix="%",
                ),
                hovertemplate="Service: %{y}<br>Tools: %{x}<br>Accuracy: %{text}%<extra></extra>",
            )
        )

        safe_name = provider.replace("/", "_")
        fig.update_layout(
            **_base_layout(
                title=dict(
                    text=f"<b>Accuracy by Service</b> - {_short(provider)}",
                    font=dict(size=20, color=_TEXT, family=_FONT),
                    x=0.03,
                    xanchor="left",
                ),
                xaxis=dict(
                    title=dict(text="TOOL COUNT", font=dict(size=11, color=_TEXT_MUTED)),
                    tickfont=dict(size=12, color=_TEXT_MUTED),
                    side="bottom",
                ),
                yaxis=dict(
                    title=dict(text="SERVICE", font=dict(size=11, color=_TEXT_MUTED)),
                    tickfont=dict(size=12, color=_TEXT_MUTED),
                    autorange="reversed",
                ),
                margin=dict(l=100, r=35, t=80, b=60),
            )
        )
        _save(fig, output_dir, f"heatmap_{safe_name}", w=1000, h=500, title=f"Service Heatmap: {_short(provider)}")


# ---------------------------------------------------------------------------
# CHART 7: Error breakdown (wrong tool vs wrong service vs API failure)
# ---------------------------------------------------------------------------


def _chart_error_breakdown(df: pd.DataFrame, output_dir: Path) -> None:
    providers = sorted(df["provider"].unique())

    rows = []
    for provider in providers:
        for num_tools in sorted(df["num_tools"].unique()):
            subset = df[(df["provider"] == provider) & (df["num_tools"] == num_tools)]
            total = len(subset)
            if total == 0:
                continue
            correct = subset["correct"].sum()
            api_errors = (subset["actual_tool"].isna()).sum()
            cross_svc = subset["cross_service_error"].sum()
            wrong_same_svc = total - correct - api_errors - cross_svc

            rows.append(
                {
                    "provider": provider,
                    "num_tools": num_tools,
                    "Correct": correct / total * 100,
                    "Wrong (same service)": max(0, wrong_same_svc) / total * 100,
                    "Wrong (cross-service)": cross_svc / total * 100,
                    "API error": api_errors / total * 100,
                }
            )

    if not rows:
        return

    breakdown = pd.DataFrame(rows)
    categories = ["Correct", "Wrong (same service)", "Wrong (cross-service)", "API error"]
    cat_colors = [_GREEN, _ORANGE, _RED, _GRAY]

    fig = make_subplots(
        rows=1,
        cols=len(providers),
        subplot_titles=[f"<b>{_short(p)}</b>" for p in providers],
        shared_yaxes=True,
        horizontal_spacing=0.05,
    )

    for pi, provider in enumerate(providers, 1):
        pdf = breakdown[breakdown["provider"] == provider].sort_values("num_tools")
        for ci, (cat, color) in enumerate(zip(categories, cat_colors)):
            fig.add_trace(
                go.Bar(
                    x=[str(t) for t in pdf["num_tools"]],
                    y=pdf[cat],
                    name=cat,
                    marker_color=color,
                    marker_opacity=0.85,
                    showlegend=(pi == 1),
                    legendgroup=cat,
                ),
                row=1,
                col=pi,
            )

    for i in range(1, len(providers) + 1):
        fig.update_xaxes(row=1, col=i, showgrid=False, tickfont=dict(size=10, color=_TEXT_MUTED))
    fig.update_yaxes(row=1, col=1, ticksuffix="%", tickfont=dict(size=10, color=_TEXT_MUTED))

    styled = []
    for a in fig.layout.annotations:
        a.update(font=dict(size=14, color=_TEXT, family=_FONT))
        styled.append(a)

    fig.update_layout(
        **_base_layout(
            title=dict(
                text="<b>Error Breakdown by Model</b>",
                font=dict(size=22, color=_TEXT, family=_FONT),
                x=0.03,
                xanchor="left",
            ),
            barmode="stack",
            annotations=styled,
            margin=dict(l=65, r=35, t=100, b=80),
            xaxis=dict(title=dict(text="TOOL COUNT", font=dict(size=11, color=_TEXT_MUTED))),
        )
    )
    _save(fig, output_dir, "error_breakdown", w=1200, h=550, title="Error Breakdown")


# ---------------------------------------------------------------------------
# CHART 8: "The Fix" - late disclosure side-by-side
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
        ("accuracy", "%", 1, 1),
        ("cross_svc", "%", 1, 2),
        ("avg_input", "tok", 2, 1),
        ("avg_latency", "ms", 2, 2),
    ]

    for metric, suffix, row, col in metrics:
        for mode in modes_present:
            mdf = agg[agg["mode"] == mode].sort_values("provider")
            short_names = [_short(p) for p in mdf["provider"]]
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

    for r, c_idx in [(1, 1), (1, 2), (2, 1), (2, 2)]:
        fig.update_xaxes(
            row=r,
            col=c_idx,
            showgrid=False,
            tickfont=dict(size=10, color=_TEXT_MUTED),
            linecolor=_BORDER,
            linewidth=1,
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

    styled = []
    for a in fig.layout.annotations:
        a.update(font=dict(size=12, color=_TEXT_MUTED, family=_FONT))
        styled.append(a)

    fig.update_layout(
        **_base_layout(
            title=dict(
                text=f"<b>Late Tool Disclosure</b>{subtitle}",
                font=dict(size=22, color=_TEXT, family=_FONT),
                x=0.03,
                xanchor="left",
            ),
            margin=dict(l=60, r=30, t=110, b=60),
            barmode="group",
            bargap=0.25,
            bargroupgap=0.06,
            annotations=styled,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.10,
                xanchor="center",
                x=0.5,
                font=dict(size=12, color=_TEXT),
                bgcolor="rgba(0,0,0,0)",
            ),
        )
    )
    _save(fig, output_dir, "hero_disclosure", w=1200, h=800, title="Late Disclosure Comparison")


# ---------------------------------------------------------------------------
# Index page
# ---------------------------------------------------------------------------


def _build_index(
    output_dir: Path,
    run_id: str,
    providers: list[str],
    total_calls: int,
    total_cost: float,
    modes: list[str],
    tool_range: str,
    df: pd.DataFrame | None = None,
) -> None:
    cards = ""
    for filename, title in _generated_charts:
        cards += f"""
        <a href="{filename}" class="card">
            <div class="card-title">{title}</div>
            <iframe src="{filename}" loading="lazy"></iframe>
            <div class="card-overlay">Click to view</div>
        </a>"""

    # Build raw data table
    data_table = ""
    if df is not None and len(df) > 0:
        has_cost = "cost_usd" in df.columns and df["cost_usd"].sum() > 0
        grouped = (
            df.groupby(["provider", "num_tools"])
            .agg(
                accuracy=("correct", "mean"),
                cross_svc=("cross_service_error", "mean"),
                avg_latency=("latency_ms", "mean"),
                avg_tokens=("input_tokens", "mean"),
                cost=("cost_usd", "sum") if has_cost else ("correct", "count"),
                calls=("correct", "count"),
            )
            .reset_index()
        )

        rows = ""
        for _, r in grouped.iterrows():
            cost_cell = f"${r['cost']:.4f}" if has_cost else "—"
            rows += f"""
            <tr>
                <td>{_short(r["provider"])}</td>
                <td>{int(r["num_tools"])}</td>
                <td>{r["accuracy"] * 100:.1f}%</td>
                <td>{r["cross_svc"] * 100:.1f}%</td>
                <td>{r["avg_latency"]:.0f}ms</td>
                <td>{r["avg_tokens"]:.0f}</td>
                <td>{cost_cell}</td>
                <td>{int(r["calls"])}</td>
            </tr>"""

        data_table = f"""
    <div class="data-section">
        <h2 class="section-title">Raw Data</h2>
        <div class="table-wrap">
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Model</th>
                        <th>Tools</th>
                        <th>Accuracy</th>
                        <th>Cross-Svc Error</th>
                        <th>Avg Latency</th>
                        <th>Avg Tokens</th>
                        <th>Cost</th>
                        <th>Calls</th>
                    </tr>
                </thead>
                <tbody>{rows}
                </tbody>
            </table>
        </div>
    </div>"""

    provider_tags = " ".join(f'<span class="tag">{_short(p)}</span>' for p in providers)
    mode_tags = " ".join(f'<span class="tag">{m}</span>' for m in modes)
    cost_str = f"${total_cost:.4f}" if total_cost > 0 else "n/a"
    run_label = run_id or "all"

    # SixDegree logo SVG path (from common-ui Logo component)
    logo_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="21" height="21" viewBox="246 270 238.2 294">'
        '<defs><linearGradient id="lg" x1="0%" y1="0%" x2="100%" y2="100%">'
        '<stop offset="0%" stop-color="#1e40af"/><stop offset="100%" stop-color="#60a5fa"/>'
        "</linearGradient></defs>"
        '<g transform="matrix(0.1,0,0,-0.1,-51,1096.903)">'
        '<path fill="url(#lg)" d="m 3960,8053 c -102,-63 -313,-194 -470,-291 -157,-96 -315,-195 '
        "-352,-219 l -68,-43 v -697 l 1,-698 257,-159 c 141,-88 386,-240 545,-338 l 288,-179 "
        "237,147 c 130,81 323,202 427,267 105,66 243,151 308,190 l 119,72 -5,300 c -4,326 -8,352 "
        "-66,470 -64,128 -189,249 -308,296 -43,17 -84,24 -159,27 -146,5 -194,-14 -534,-216 "
        "-25,-15 -31,-12 -220,103 -392,238 -466,283 -497,299 -18,9 -33,18 -33,20 0,2 105,68 "
        "233,146 127,79 277,171 332,205 55,34 114,69 131,78 l 31,16 227,-145 c 125,-79 232,-144 "
        "237,-144 14,0 259,152 259,160 0,4 -33,28 -72,53 -40,24 -163,100 -273,167 -110,68 "
        "-237,147 -283,177 -45,29 -88,53 -95,52 -7,0 -95,-52 -197,-116 z M 3594,6998 c 129,-79 "
        "249,-151 266,-160 17,-10 29,-22 26,-26 -3,-5 -43,-30 -88,-57 -46,-26 -165,-99 -266,-161 "
        "-100,-63 -185,-114 -187,-114 -3,0 -5,149 -5,330 0,203 4,330 10,330 5,0 115,-64 244,-142 "
        "z m 1211,-102 c 64,-29 134,-107 158,-174 15,-42 20,-92 24,-256 l 5,-205 -39,-24 c -21,-14 "
        "-208,-129 -416,-256 l -377,-232 -248,153 c -136,85 -302,188 -369,229 -68,41 -123,77 "
        "-123,80 0,8 25,24 315,199 121,74 262,160 313,193 52,32 100,56 108,53 7,-3 88,-53 "
        "179,-111 91,-58 167,-105 169,-105 9,0 261,162 264,170 3,9 -79,59 -240,144 -60,32 "
        '-108,61 -108,65 0,11 114,71 164,87 69,21 164,17 221,-10 z"/>'
        "</g></svg>"
    )

    # GitHub icon SVG (octicon mark-github)
    gh_icon = (
        '<svg viewBox="0 0 16 16"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59'
        ".4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94"
        "-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07"
        "-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02"
        ".08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2"
        "-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95"
        ".29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8"
        'c0-4.42-3.58-8-8-8z"/></svg>'
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Boundary Results{f" - {run_id}" if run_id else ""}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Satoshi:wght@700;900&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: {_BG};
            color: {_TEXT};
            font-family: {_FONT};
            padding: 2rem;
        }}
        .header {{
            max-width: 1400px;
            margin: 0 auto 2rem;
        }}
        .brand {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1.5rem;
        }}
        .brand-left {{
            display: flex;
            flex-direction: column;
            gap: 0.2rem;
        }}
        .brand-left h1 {{
            font-family: Satoshi, system-ui, sans-serif;
            font-weight: 900;
            font-size: 1.6rem;
            letter-spacing: -0.03em;
        }}
        .brand-left h1 .b-text {{ color: {_TEXT}; }}
        .brand-left .test-name {{
            color: {_TEXT_MUTED};
            font-family: {_FONT};
            font-weight: normal;
            font-size: 0.85rem;
        }}
        .brand-right {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .brand-right {{
            gap: 1rem;
        }}
        .gh-btn {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            background: {_SURFACE};
            border: 1px solid {_BORDER};
            border-radius: 6px;
            color: {_TEXT};
            text-decoration: none;
            font-size: 0.85rem;
            font-weight: 600;
            transition: border-color 0.2s, background 0.2s;
        }}
        .gh-btn:hover {{
            border-color: #58a6ff;
            background: {_BG};
        }}
        .gh-btn svg {{
            width: 18px;
            height: 18px;
            fill: currentColor;
        }}
        .sixdegree-badge {{
            display: flex;
            align-items: center;
            gap: 1.8px;
            text-decoration: none;
            transition: opacity 0.2s;
        }}
        .sixdegree-badge:hover {{
            opacity: 0.8;
        }}
        .sixdegree-badge .sd-by {{
            color: {_TEXT_MUTED};
            font-size: 0.8rem;
            margin-right: 0.3rem;
        }}
        .sixdegree-badge .sd-logo {{
            display: flex;
            align-items: center;
            margin-left: -1.8px;
        }}
        .sixdegree-badge .sd-text {{
            font-family: Satoshi, system-ui, -apple-system, sans-serif;
            font-weight: 900;
            letter-spacing: -0.05em;
            font-size: 19.8px;
            white-space: nowrap;
            margin-top: -3.96px;
            margin-left: -1.08px;
        }}
        .sixdegree-badge .sd-six {{ color: white; }}
        .sixdegree-badge .sd-degree {{ color: #60a5fa; }}
        .stats {{
            display: flex;
            gap: 2rem;
            flex-wrap: wrap;
            padding: 1rem 1.25rem;
            background: {_SURFACE};
            border: 1px solid {_BORDER};
            border-radius: 8px;
        }}
        .stat {{
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }}
        .stat-label {{
            color: {_TEXT_MUTED};
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .stat-value {{
            font-size: 1rem;
        }}
        .tag {{
            display: inline-block;
            background: {_BG};
            border: 1px solid {_BORDER};
            border-radius: 4px;
            padding: 0.1rem 0.4rem;
            font-size: 0.75rem;
            margin-right: 0.2rem;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(580px, 1fr));
            gap: 1.5rem;
            max-width: 1400px;
            margin: 0 auto;
        }}
        .card {{
            display: block;
            background: {_SURFACE};
            border: 1px solid {_BORDER};
            border-radius: 8px;
            overflow: hidden;
            text-decoration: none;
            color: inherit;
            position: relative;
            transition: border-color 0.2s;
        }}
        .card:hover {{
            border-color: {_BLUE};
        }}
        .card-title {{
            padding: 0.75rem 1rem;
            font-size: 0.9rem;
            font-weight: 600;
            border-bottom: 1px solid {_BORDER};
        }}
        .card iframe {{
            width: 100%;
            height: 400px;
            border: none;
            pointer-events: none;
        }}
        .card-overlay {{
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 60px;
            background: linear-gradient(transparent, {_SURFACE});
            display: flex;
            align-items: flex-end;
            justify-content: center;
            padding-bottom: 0.75rem;
            font-size: 0.8rem;
            color: {_TEXT_MUTED};
            opacity: 0;
            transition: opacity 0.2s;
        }}
        .card:hover .card-overlay {{
            opacity: 1;
        }}
        .data-section {{
            max-width: 1400px;
            margin: 2rem auto;
            overflow-x: auto;
        }}
        .section-title {{
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 1rem;
            color: {_TEXT};
        }}
        .table-wrap {{
            overflow-x: auto;
        }}
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.8rem;
        }}
        .data-table th {{
            text-align: left;
            padding: 0.6rem 0.8rem;
            border-bottom: 2px solid {_BORDER};
            color: {_TEXT_MUTED};
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.7rem;
            letter-spacing: 0.05em;
        }}
        .data-table td {{
            padding: 0.5rem 0.8rem;
            border-bottom: 1px solid {_BORDER};
            color: {_TEXT};
        }}
        .data-table tr:hover {{
            background: {_SURFACE};
        }}
        .footer {{
            max-width: 1400px;
            margin: 2rem auto 0;
            padding-top: 1.5rem;
            border-top: 1px solid {_BORDER};
            display: flex;
            align-items: center;
            justify-content: space-between;
            color: {_TEXT_MUTED};
            font-size: 0.75rem;
        }}
        @media (max-width: 640px) {{
            body {{
                padding: 1rem;
            }}
            .brand {{
                flex-direction: column;
                align-items: flex-start;
                gap: 0.75rem;
            }}
            .brand-left h1 {{
                font-size: 1.3rem;
            }}
            .stats {{
                gap: 1rem;
            }}
            .stat-value {{
                font-size: 0.85rem;
            }}
            .grid {{
                grid-template-columns: 1fr;
            }}
            .card iframe {{
                height: 250px;
            }}
            .gh-btn {{
                font-size: 0.75rem;
                padding: 0.4rem 0.75rem;
            }}
            .gh-btn span {{
                display: none;
            }}
            .footer {{
                flex-direction: column;
                gap: 0.5rem;
                text-align: center;
            }}
            .data-table {{
                font-size: 0.7rem;
            }}
            .data-table th, .data-table td {{
                padding: 0.4rem 0.5rem;
            }}
        }}
        .footer a {{
            color: {_TEXT_MUTED};
            text-decoration: none;
        }}
        .footer a:hover {{
            color: {_TEXT};
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="brand">
            <div class="brand-left">
                <h1><span class="b-text">Boundary</span></h1>
                <a href="https://sixdegree.ai" class="sixdegree-badge">
                    <span class="sd-by">by</span>
                    <span class="sd-logo">{logo_svg}</span>
                    <span class="sd-text"><span class="sd-six">six</span><span class="sd-degree">degree</span></span>
                </a>
            </div>
            <div class="brand-right">
                <a href="https://github.com/sixdegree-ai/boundary" class="gh-btn">
                    {gh_icon}
                    View on GitHub
                </a>
            </div>
        </div>
        <div class="stats">
            <div class="stat">
                <div class="stat-label">Test</div>
                <div class="stat-value">tool-overload</div>
            </div>
            <div class="stat">
                <div class="stat-label">Run</div>
                <div class="stat-value"><code>{run_label}</code></div>
            </div>
            <div class="stat">
                <div class="stat-label">Models</div>
                <div class="stat-value">{provider_tags}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Modes</div>
                <div class="stat-value">{mode_tags}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Tool range</div>
                <div class="stat-value">{tool_range}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Total calls</div>
                <div class="stat-value">{total_calls:,}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Total cost</div>
                <div class="stat-value" style="color: {_GREEN}">{cost_str}</div>
            </div>
        </div>
    </div>
    <div class="grid">
        {cards}
    </div>
    <div style="max-width:1400px;margin:2rem auto 0">
        <a href="data.html" class="gh-btn">View Raw Data</a>
    </div>
    <div class="footer">
        <span>Generated by <a href="https://github.com/sixdegree-ai/boundary">Boundary</a></span>
        <a href="https://sixdegree.ai">sixdegree.ai</a>
    </div>
</body>
</html>"""

    index_path = output_dir / "index.html"
    index_path.write_text(html)
    console.print("  [green]Saved index.html[/green]")

    # Write data page
    if data_table:
        data_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Boundary Data - {run_label}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Satoshi:wght@700;900&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: {_BG};
            color: {_TEXT};
            font-family: JetBrains Mono, SF Mono, Consolas, monospace;
            padding: 2rem;
        }}
        .header {{
            max-width: 1400px;
            margin: 0 auto 2rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .back {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            color: {_TEXT_MUTED};
            text-decoration: none;
            font-size: 0.85rem;
            transition: color 0.2s;
        }}
        .back:hover {{ color: {_TEXT}; }}
        h1 {{
            font-family: Satoshi, system-ui, sans-serif;
            font-weight: 900;
            font-size: 1.4rem;
            letter-spacing: -0.03em;
        }}
        .data-section {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .table-wrap {{
            overflow-x: auto;
        }}
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.8rem;
        }}
        .data-table th {{
            text-align: left;
            padding: 0.6rem 0.8rem;
            border-bottom: 2px solid {_BORDER};
            color: {_TEXT_MUTED};
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.7rem;
            letter-spacing: 0.05em;
            cursor: pointer;
            user-select: none;
        }}
        .data-table th:hover {{
            color: {_TEXT};
        }}
        .data-table td {{
            padding: 0.5rem 0.8rem;
            border-bottom: 1px solid {_BORDER};
            color: {_TEXT};
        }}
        .data-table tr:hover {{
            background: {_SURFACE};
        }}
    </style>
</head>
<body>
    <div class="header">
        <a href="index.html" class="back">&larr; Back to charts</a>
        <h1>Raw Data &mdash; <code>{run_label}</code></h1>
    </div>
    {data_table}
</body>
</html>"""
        data_path = output_dir / "data.html"
        data_path.write_text(data_html)
        console.print("  [green]Saved data.html[/green]")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hex_to_rgb(hex_color: str) -> str:
    """'#58a6ff' -> '88, 166, 255'"""
    h = hex_color.lstrip("#")
    return f"{int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}"
