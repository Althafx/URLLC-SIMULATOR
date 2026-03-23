"""Plotly charts for the URLLC simulation dashboard."""

from __future__ import annotations

from typing import Any, Dict, List

import plotly.graph_objects as go

from simulation.metrics import PACKET_TYPES

BG = "#0a0b10"
PANEL = "#111318"
GRID = "rgba(100, 200, 255, 0.08)"
TEXT = "#d1d5db"
ACCENT = "#67e8f9"

COLORS = {"URLLC": "#22d3ee", "eMBB": "#f472b6", "IoT": "#a78bfa"}
EDGES = {"URLLC": "#67e8f9", "eMBB": "#fbcfe8", "IoT": "#ddd6fe"}


def comparison_table(results_list: List[Dict[str, Any]]) -> Dict[str, Dict[str, List[float]]]:
    """Extract per-type avg_latency, loss %, reliability % aligned with results_list order."""
    out: Dict[str, Dict[str, List[float]]] = {
        "avg_latency": {t: [] for t in PACKET_TYPES},
        "packet_loss_pct": {t: [] for t in PACKET_TYPES},
        "reliability_pct": {t: [] for t in PACKET_TYPES},
    }
    for res in results_list:
        for t in PACKET_TYPES:
            b = res["by_type"][t]
            al = b.get("avg_latency")
            out["avg_latency"][t].append(float("nan") if al is None else float(al))
            out["packet_loss_pct"][t].append(float(b["packet_loss_rate"]) * 100.0)
            out["reliability_pct"][t].append(float(b["reliability_pct"]))
    return out


def mode_labels(results_list: List[Dict[str, Any]]) -> List[str]:
    return [
        "URLLC ON" if r.get("urllc_enabled") else "Normal"
        for r in results_list
    ]


def plotly_grouped_bar(
    categories: List[str],
    series: Dict[str, List[float]],
    title: str,
    yaxis_title: str,
    yaxis_range: List[float] | None = None,
) -> go.Figure:
    traces = []
    for t in PACKET_TYPES:
        traces.append(
            go.Bar(
                name=t,
                x=categories,
                y=series[t],
                marker=dict(color=COLORS[t], line=dict(color=EDGES[t], width=1), opacity=0.92),
                texttemplate="%{y:.2f}",
                textposition="outside",
                textfont=dict(size=11, color=TEXT),
            )
        )
    layout = dict(
        paper_bgcolor=BG,
        plot_bgcolor=PANEL,
        font=dict(family="Segoe UI, sans-serif", color=TEXT, size=12),
        title=dict(text=f"<b>{title}</b>", font=dict(size=15, color=ACCENT), x=0.01),
        barmode="group",
        bargap=0.25,
        xaxis=dict(linecolor="#334155", tickfont=dict(color=TEXT), showgrid=False),
        yaxis=dict(
            title=yaxis_title,
            gridcolor=GRID,
            linecolor="#334155",
            tickfont=dict(color=TEXT),
            range=yaxis_range,
            rangemode="tozero",
        ),
        legend=dict(
            orientation="h", y=1.08, x=0.5, xanchor="center",
            bgcolor="rgba(17,19,24,0.8)", font=dict(color=TEXT, size=11),
        ),
        margin=dict(l=50, r=16, t=65, b=40),
        hoverlabel=dict(bgcolor="#1e293b"),
    )
    return go.Figure(data=traces, layout=layout)


def plotly_latency_condition_lines(normal_res: Dict[str, Any], heavy_res: Dict[str, Any]) -> go.Figure:
    """
    Single clean comparison chart:
    latency per class under Normal vs Heavy traffic conditions.
    """
    conditions = ["Normal traffic", "Heavy traffic"]
    fig = go.Figure()
    for t in PACKET_TYPES:
        n = normal_res["by_type"][t].get("avg_latency")
        h = heavy_res["by_type"][t].get("avg_latency")
        ys = [
            float("nan") if n is None else float(n),
            float("nan") if h is None else float(h),
        ]
        fig.add_trace(
            go.Scatter(
                x=conditions,
                y=ys,
                mode="lines+markers",
                name=t,
                line=dict(color=COLORS[t], width=3),
                marker=dict(size=9, color=COLORS[t], line=dict(color=EDGES[t], width=1)),
            )
        )
    fig.update_layout(
        paper_bgcolor=BG,
        plot_bgcolor=PANEL,
        font=dict(family="Segoe UI, sans-serif", color=TEXT, size=12),
        title=dict(text="<b>Latency by Traffic Condition</b>", font=dict(size=16, color=ACCENT), x=0.01),
        xaxis=dict(title="Traffic condition", linecolor="#334155", tickfont=dict(color=TEXT), showgrid=False),
        yaxis=dict(title="Latency (sim units)", gridcolor=GRID, linecolor="#334155", tickfont=dict(color=TEXT), rangemode="tozero"),
        legend=dict(
            orientation="h",
            y=1.08,
            x=0.5,
            xanchor="center",
            bgcolor="rgba(17,19,24,0.8)",
            font=dict(color=TEXT, size=11),
        ),
        margin=dict(l=52, r=16, t=70, b=46),
        hoverlabel=dict(bgcolor="#1e293b"),
    )
    return fig


def plotly_chart_config() -> dict:
    return {"displayModeBar": False}
