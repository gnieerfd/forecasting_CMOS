"""
components/charts.py
Reusable Plotly chart builders for CMOS. Dark theme palette.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

_BG   = "#0e1117"
_CARD = "#1c2333"
_GRID = "#1e2a3a"
_FONT = "#e8eaf6"
_ACC1 = "#00d4aa"
_ACC2 = "#ff6b9d"
_ACC3 = "#ffd166"


def _base_layout(**kwargs) -> dict:
    base = dict(
        paper_bgcolor=_BG,
        plot_bgcolor=_CARD,
        font=dict(family="Segoe UI, sans-serif", color=_FONT, size=12),
        xaxis=dict(gridcolor=_GRID, linecolor=_GRID, zerolinecolor=_GRID),
        yaxis=dict(gridcolor=_GRID, linecolor=_GRID, zerolinecolor=_GRID),
        legend=dict(bgcolor="rgba(0,0,0,0.35)", bordercolor="#2a3348", borderwidth=1),
        margin=dict(l=50, r=20, t=50, b=50),
        hovermode="x unified",
    )
    base.update(kwargs)
    return base


def forecast_line_chart(
    df_hist: pd.DataFrame,
    df_pred: pd.DataFrame,
    date_col: str = "Tanggal",
    actual_col: str = "Aktual",
    pred_col: str = "Prediksi",
) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_hist[date_col], y=df_hist[actual_col],
        name="Historis (Aktual)", mode="lines",
        line=dict(color=_ACC1, width=2),
        hovertemplate="%{x|%d %b %Y}<br>Aktual: <b>%{y:.2f} kWh</b><extra></extra>",
    ))
    if actual_col in df_pred.columns:
        fig.add_trace(go.Scatter(
            x=df_pred[date_col], y=df_pred[actual_col],
            name="Aktual (Test)", mode="lines",
            line=dict(color=_ACC3, width=2, dash="dot"),
        ))
    fig.add_trace(go.Scatter(
        x=df_pred[date_col], y=df_pred[pred_col],
        name="Prediksi (XGBoost)", mode="lines+markers",
        line=dict(color=_ACC2, width=2.5),
        marker=dict(size=4, color=_ACC2),
        hovertemplate="%{x|%d %b %Y}<br>Prediksi: <b>%{y:.2f} kWh</b><extra></extra>",
    ))
    fig.update_layout(**_base_layout(
        title=dict(text="📈 Forecasting – Historis vs Prediksi", font=dict(size=16)),
        xaxis_title="Tanggal",
        yaxis_title="Energy Demand EV (kWh)",
    ))
    return fig


def feature_importance_bar(feat_series: pd.Series) -> go.Figure:
    top10 = feat_series.head(10)
    fig = go.Figure(go.Bar(
        x=top10.values, y=top10.index, orientation="h",
        marker=dict(color=top10.values, colorscale=[[0, "#1c2333"], [1, _ACC1]]),
    ))
    fig.update_layout(**_base_layout(
        title=dict(text="🔍 Feature Importance", font=dict(size=14)),
        xaxis_title="Score",
        yaxis=dict(autorange="reversed", gridcolor=_GRID),
        margin=dict(l=130, r=20, t=50, b=40),
    ))
    return fig


def realtime_energy_line(df_today: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Scatter(
        x=df_today["Time_Stamp"], y=df_today["Energy_Trafo_2"],
        mode="lines+markers",
        line=dict(color=_ACC1, width=2.5),
        marker=dict(size=5, color=_ACC1),
        fill="tozeroy",
        fillcolor="rgba(0,212,170,0.08)",
        hovertemplate="%{x|%H:%M:%S}<br>Energi: <b>%{y:.2f} kWh</b><extra></extra>",
    ))
    fig.update_layout(**_base_layout(
        title=dict(text="⚡ Real-time Energy – Hari Ini", font=dict(size=14)),
        xaxis_title="Waktu",
        yaxis_title="Energy Trafo 2 (kWh)",
    ))
    return fig


def daily_energy_bar(df_daily: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Bar(
        x=df_daily["Date"].astype(str),
        y=df_daily["Energy_kWh"],
        marker=dict(
            color=df_daily["Energy_kWh"],
            colorscale=[[0, "#1a3d6b"], [1, _ACC1]],
            line=dict(width=0),
        ),
        hovertemplate="%{x}<br>Energi: <b>%{y:,.0f} kWh</b><extra></extra>",
    ))
    fig.update_layout(**_base_layout(
        title=dict(text="Daily Energy Consumption", font=dict(size=13, color=_FONT)),
        xaxis_title="Tanggal",
        yaxis_title="Energi (kWh)",
        yaxis=dict(tickformat=".2s", gridcolor=_GRID),
        xaxis=dict(tickangle=-30, gridcolor=_GRID),
        margin=dict(l=60, r=10, t=50, b=80),
    ))
    return fig


def top5_daily_donut(df_daily: pd.DataFrame) -> go.Figure:
    top5 = df_daily.nlargest(5, "Energy_kWh").copy()
    top5["Label"] = top5["Date"].astype(str)
    fig = go.Figure(go.Pie(
        labels=top5["Label"],
        values=top5["Energy_kWh"],
        hole=0.5,
        textinfo="percent",
        hovertemplate="%{label}<br>%{value:,.0f} kWh<br>%{percent}<extra></extra>",
        marker=dict(
            colors=["#1a5fa8", "#2176ae", "#3a86c0", "#6baed6", "#c6e2f5"],
            line=dict(color=_BG, width=2),
        ),
    ))
    fig.update_layout(**_base_layout(
        title=dict(text="Top 5 Daily Energy", font=dict(size=13, color=_FONT)),
        showlegend=True,
        legend=dict(orientation="v", bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
        margin=dict(l=10, r=10, t=50, b=20),
    ))
    return fig