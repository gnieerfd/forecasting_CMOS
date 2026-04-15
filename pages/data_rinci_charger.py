"""
pages/data_rinci_charger.py
Data Rinci Charger – Detail spesifikasi & status setiap unit charger.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go

_rng = np.random.default_rng(21)

_CHARGERS = pd.DataFrame([
    {"charger_id": "CHR-001", "station":  "CS Serpong",  "tipe": "AC Level 2", "daya_kw": 22,   "konektor": "Type 2",    "status": "Available",   "sn": "SN-A001"},
    {"charger_id": "CHR-002", "station":  "CS Serpong",  "tipe": "DC Fast",     "daya_kw": 50,   "konektor": "CCS2",      "status": "Charging",    "sn": "SN-A002"},
    {"charger_id": "CHR-003", "station":  "CS Serpong",  "tipe": "DC Fast",     "daya_kw": 50,   "konektor": "CCS2",      "status": "Charging",    "sn": "SN-A003"},
    {"charger_id": "CHR-004", "station":  "CS Serpong",  "tipe": "AC Level 2",  "daya_kw": 7.4,  "konektor": "Type 2",    "status": "Faulted",     "sn": "SN-A004"},
    {"charger_id": "CHR-005", "station":  "CS BSD City", "tipe": "DC Ultra",    "daya_kw": 150,  "konektor": "CCS2",      "status": "Charging",    "sn": "SN-B001"},
    {"charger_id": "CHR-006", "station":  "CS BSD City", "tipe": "DC Ultra",    "daya_kw": 150,  "konektor": "CCS2",      "status": "Available",   "sn": "SN-B002"},
    {"charger_id": "CHR-007", "station":  "CS BSD City", "tipe": "AC Level 2",  "daya_kw": 22,   "konektor": "Type 2",    "status": "Charging",    "sn": "SN-B003"},
    {"charger_id": "CHR-008", "station":  "CS Bekasi",   "tipe": "DC Fast",     "daya_kw": 50,   "konektor": "CHAdeMO",   "status": "Available",   "sn": "SN-C001"},
    {"charger_id": "CHR-009", "station":  "CS Bekasi",   "tipe": "AC Level 2",  "daya_kw": 7.4,  "konektor": "Type 2",    "status": "Unavailable", "sn": "SN-C002"},
    {"charger_id": "CHR-010", "station":  "CS Karawang", "tipe": "DC Fast",     "daya_kw": 60,   "konektor": "CCS2",      "status": "Charging",    "sn": "SN-D001"},
])
_CHARGERS["uptime_pct"] = _rng.uniform(88, 99.9, len(_CHARGERS)).round(1)
_CHARGERS["energy_month_kwh"] = _rng.uniform(200, 3500, len(_CHARGERS)).round(1)
_CHARGERS["sesi_bulan"] = _rng.integers(15, 280, len(_CHARGERS))

_STATUS_COLOR = {
    "Available":   "#00d4aa",
    "Charging":    "#3a86ff",
    "Faulted":     "#ff4b6e",
    "Unavailable": "#ffd166",
}


def render_data_rinci_charger() -> None:
    st.markdown(
        "<h1 style='font-size:2rem;font-weight:800;margin-bottom:0.2rem;'>"
        "🔌 Data Rinci Charger</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#8892a4;margin-bottom:1.4rem;'>"
        "Spesifikasi teknis, status operasional, dan statistik penggunaan setiap unit charger.</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    # ── Filter bar ───────────────────────────────────────────────────────
    fc1, fc2, fc3 = st.columns(3)
    stations = ["Semua"] + sorted(_CHARGERS["station"].unique().tolist())
    sel_station = fc1.selectbox(" Stasiun", stations)
    statuses = ["Semua"] + sorted(_CHARGERS["status"].unique().tolist())
    sel_status  = fc2.selectbox(" Status", statuses)
    types = ["Semua"] + sorted(_CHARGERS["tipe"].unique().tolist())
    sel_type    = fc3.selectbox(" Tipe", types)

    df = _CHARGERS.copy()
    if sel_station != "Semua": df = df[df["station"] == sel_station]
    if sel_status  != "Semua": df = df[df["status"]  == sel_status]
    if sel_type    != "Semua": df = df[df["tipe"]    == sel_type]

    # ── KPIs ─────────────────────────────────────────────────────────────
    st.divider()
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(" Total Charger",     len(df))
    k2.metric(" Sedang Charging",   (df["status"]=="Charging").sum())
    k3.metric(" Total Energi Bulan", f"{df['energy_month_kwh'].sum():,.0f} kWh")
    k4.metric(" Total Sesi Bulan",  f"{df['sesi_bulan'].sum():,}")
    st.divider()

    # ── Charger cards ────────────────────────────────────────────────────
    st.markdown("#### Daftar Unit Charger")
    cols_per_row = 3
    rows = [df.iloc[i:i+cols_per_row] for i in range(0, len(df), cols_per_row)]
    for row_df in rows:
        cols = st.columns(cols_per_row, gap="medium")
        for col, (_, ch) in zip(cols, row_df.iterrows()):
            c = _STATUS_COLOR.get(ch["status"], "#aaa")
            with col:
                st.markdown(
                    f"""
                    <div style="background:#1c2333;border:1px solid #2a3348;border-radius:10px;
                                padding:14px 16px;margin-bottom:10px;min-height:190px;">
                      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                        <span style="font-size:1rem;font-weight:700;">{ch['charger_id']}</span>
                        <span style="background:{c}22;color:{c};border:1px solid {c};border-radius:4px;
                                     padding:1px 8px;font-size:0.72rem;font-weight:700;">{ch['status']}</span>
                      </div>
                      <div style="color:#8892a4;font-size:0.8rem;line-height:1.9;">
                         {ch['station']}<br>
                         {ch['tipe']} – <b style='color:#e8eaf6'>{ch['daya_kw']} kW</b><br>
                         Konektor: {ch['konektor']}<br>
                         S/N: {ch['sn']}<br>
                         Uptime: <b style='color:{c}'>{ch['uptime_pct']}%</b><br>
                         Energi Bulan: {ch['energy_month_kwh']:,.0f} kWh<br>
                         Sesi Bulan: {ch['sesi_bulan']}
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.divider()

    # ── Charts ───────────────────────────────────────────────────────────
    ch1, ch2 = st.columns(2, gap="medium")
    with ch1:
        st.markdown("#### Energi per Charger (Bulan Ini)")
        df_s = df.sort_values("energy_month_kwh", ascending=True)
        fig = go.Figure(go.Bar(
            x=df_s["energy_month_kwh"], y=df_s["charger_id"], orientation="h",
            marker=dict(color=df_s["energy_month_kwh"], colorscale=[[0,"#1a3d6b"],[1,"#00d4aa"]], line=dict(width=0)),
            hovertemplate="%{y}: %{x:,.0f} kWh<extra></extra>",
        ))
        fig.update_layout(
            paper_bgcolor="#0e1117", plot_bgcolor="#1c2333",
            xaxis=dict(title="kWh", gridcolor="#1e2a3a", color="#e8eaf6"),
            yaxis=dict(gridcolor="#1e2a3a", color="#e8eaf6"),
            font=dict(color="#e8eaf6"), margin=dict(l=20,r=10,t=20,b=40), height=300,
        )
        st.plotly_chart(fig, use_container_width=True)

    with ch2:
        st.markdown("#### Distribusi Status")
        sc = df["status"].value_counts().reset_index()
        sc.columns = ["status", "count"]
        colors = [_STATUS_COLOR.get(s, "#aaa") for s in sc["status"]]
        fig2 = go.Figure(go.Pie(
            labels=sc["status"], values=sc["count"], hole=0.5,
            marker=dict(colors=colors, line=dict(color="#0e1117", width=2)),
            textinfo="label+percent",
            hovertemplate="%{label}: %{value} unit<extra></extra>",
        ))
        fig2.update_layout(
            paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
            font=dict(color="#e8eaf6"), margin=dict(l=20,r=20,t=20,b=20), height=300,
            showlegend=False,
        )
        st.plotly_chart(fig2, use_container_width=True)
