
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go

_STATIONS = pd.DataFrame([
    {"id": "CS_Serpong",  "nama": "CS Serpong",  "lat": -6.3194, "lon": 106.6548, "kota": "Tangerang Selatan", "status": "Online",  "connector": 4, "active": 3, "energy_today_kwh": 128.4},
    {"id": "CS_Bekasi",   "nama": "CS Bekasi",   "lat": -6.2349, "lon": 106.9896, "kota": "Bekasi",            "status": "Online",  "connector": 2, "active": 1, "energy_today_kwh":  55.2},
    {"id": "CS_Depok",    "nama": "CS Depok",    "lat": -6.4025, "lon": 106.7942, "kota": "Depok",             "status": "Offline", "connector": 2, "active": 0, "energy_today_kwh":   0.0},
    {"id": "CS_BSD",      "nama": "CS BSD City", "lat": -6.3010, "lon": 106.6530, "kota": "Tangerang",         "status": "Online",  "connector": 6, "active": 4, "energy_today_kwh": 213.1},
    {"id": "CS_Karawang", "nama": "CS Karawang", "lat": -6.3220, "lon": 107.3381, "kota": "Karawang",          "status": "Online",  "connector": 2, "active": 2, "energy_today_kwh":  87.9},
])
_STATUS_COLOR = {"Online": "#00d4aa", "Offline": "#ff4b6e", "Maintenance": "#ffd166"}


def render_dashboard_lokasi() -> None:
    st.markdown(
        "<h1 style='font-size:2rem;font-weight:800;margin-bottom:0.2rem;'>"
        "Dashboard Lokasi Charging Station</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#8892a4;margin-bottom:1.4rem;'>"
        "Ringkasan operasional seluruh titik pengisian EV di CMOS.</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    # ── KPI ───────────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total CS",        len(_STATIONS))
    k2.metric("CS Online",       (_STATIONS["status"] == "Online").sum())
    k3.metric("Total Konektor",  _STATIONS["connector"].sum())
    k4.metric("Konektor Aktif",  _STATIONS["active"].sum())
    k5.metric("Energi Hari Ini", f"{_STATIONS['energy_today_kwh'].sum():,.1f} kWh")
    st.divider()

    col_map, col_tbl = st.columns([1.6, 1], gap="large")

    with col_map:
        st.markdown("#### Peta Stasiun")
        colors = [_STATUS_COLOR.get(s, "#aaa") for s in _STATIONS["status"]]

        fig = go.Figure()
        fig.add_trace(go.Scattermapbox(
            lat=_STATIONS["lat"].tolist(),
            lon=_STATIONS["lon"].tolist(),
            mode="markers+text",
            marker=dict(size=18, color=colors, opacity=0.9),
            text=_STATIONS["nama"].tolist(),
            textposition="top right",
            customdata=_STATIONS[["nama", "status", "active", "connector", "energy_today_kwh"]].values,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Status: %{customdata[1]}<br>"
                "Konektor: %{customdata[2]}/%{customdata[3]} aktif<br>"
                "Energi: %{customdata[4]:.1f} kWh<extra></extra>"
            ),
            name="",
            showlegend=False,
        ))
        fig.update_layout(
            mapbox=dict(
                style="carto-darkmatter",
                center=dict(lat=-6.35, lon=106.82),
                zoom=9,
            ),
            paper_bgcolor="#0e1117",
            margin=dict(l=0, r=0, t=10, b=0),
            height=420,
            font=dict(color="#e8eaf6"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_tbl:
        st.markdown("#### Status Stasiun")
        for _, row in _STATIONS.iterrows():
            c   = _STATUS_COLOR.get(row["status"], "#aaa")
            pct = int(row["active"] / row["connector"] * 100) if row["connector"] else 0
            st.markdown(
                f"""
                <div style="background:#1c2333;border:1px solid #2a3348;border-radius:8px;
                            padding:10px 14px;margin-bottom:8px;">
                  <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span style="font-weight:700;font-size:0.95rem;">{row['nama']}</span>
                    <span style="background:{c}22;color:{c};border:1px solid {c};
                                 border-radius:4px;padding:1px 8px;font-size:0.75rem;">
                      {row['status']}
                    </span>
                  </div>
                  <div style="color:#8892a4;font-size:0.8rem;margin-top:4px;">
                    {row['kota']} · {row['active']}/{row['connector']} aktif ·
                    ⚡ {row['energy_today_kwh']:.1f} kWh
                  </div>
                  <div style="background:#0e1117;border-radius:4px;height:5px;margin-top:8px;">
                    <div style="background:{c};width:{pct}%;height:5px;border-radius:4px;"></div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.divider()
    st.markdown("#### Energi Hari Ini per Stasiun")
    df_bar = _STATIONS.sort_values("energy_today_kwh", ascending=True)
    fig2 = go.Figure(go.Bar(
        x=df_bar["energy_today_kwh"], y=df_bar["nama"], orientation="h",
        marker=dict(color=df_bar["energy_today_kwh"],
                    colorscale=[[0, "#1a3d6b"], [1, "#00d4aa"]],
                    line=dict(width=0)),
        hovertemplate="%{y}<br>%{x:.1f} kWh<extra></extra>",
    ))
    fig2.update_layout(
        paper_bgcolor="#0e1117", plot_bgcolor="#1c2333",
        xaxis=dict(title="Energi (kWh)", gridcolor="#1e2a3a", color="#e8eaf6"),
        yaxis=dict(gridcolor="#1e2a3a", color="#e8eaf6"),
        font=dict(color="#e8eaf6"), margin=dict(l=20, r=20, t=20, b=40), height=260,
    )
    st.plotly_chart(fig2, use_container_width=True)