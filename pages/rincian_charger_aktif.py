"""
pages/rincian_charger_aktif.py
Rincian Charger Aktif – live status charger yang sedang melayani sesi.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta

_rng = np.random.default_rng(77)

_ACTIVE = [
    {"charger_id":"CHR-002","station":"CS Serpong",  "connector":2,"id_tag":"RFID-1003",
     "start":"2026-04-12 09:15:00","energy_kwh":18.4,"power_kw":48.5,"soc":62,"voltage":400,"current":121},
    {"charger_id":"CHR-003","station":"CS Serpong",  "connector":1,"id_tag":"RFID-1011",
     "start":"2026-04-12 10:02:00","energy_kwh": 7.1,"power_kw":22.0,"soc":35,"voltage":230,"current": 96},
    {"charger_id":"CHR-005","station":"CS BSD City", "connector":1,"id_tag":"RFID-1027",
     "start":"2026-04-12 08:50:00","energy_kwh":42.3,"power_kw":142.0,"soc":81,"voltage":800,"current":178},
    {"charger_id":"CHR-007","station":"CS BSD City", "connector":2,"id_tag":"RFID-1009",
     "start":"2026-04-12 10:30:00","energy_kwh": 3.5,"power_kw":7.4,"soc":22,"voltage":230,"current": 32},
    {"charger_id":"CHR-010","station":"CS Karawang", "connector":1,"id_tag":"RFID-1019",
     "start":"2026-04-12 09:45:00","energy_kwh":25.8,"power_kw":58.0,"soc":55,"voltage":400,"current":145},
]

def _elapsed(start_str: str) -> str:
    start = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
    delta = datetime.now() - start
    total = int(delta.total_seconds())
    h, rem = divmod(total, 3600)
    m, s   = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def _soc_bar(pct: int, width: int = 120) -> str:
    color = "#00d4aa" if pct > 50 else "#ffd166" if pct > 20 else "#ff4b6e"
    return (
        f"<div style='background:#0e1117;border-radius:4px;height:8px;width:{width}px;display:inline-block;'>"
        f"<div style='background:{color};width:{pct}%;height:8px;border-radius:4px;'></div></div>"
    )


def render_rincian_charger_aktif() -> None:
    st.markdown(
        "<h1 style='font-size:2rem;font-weight:800;margin-bottom:0.2rem;'>"
        "⚡ Rincian Charger Aktif</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#8892a4;margin-bottom:1.4rem;'>"
        "Status live charger yang saat ini sedang melayani sesi pengisian EV.</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    # ── KPIs ──────────────────────────────────────────────────────────────
    k1, k2, k3 = st.columns(3)
    k1.metric("⚡ Charger Aktif",       len(_ACTIVE))
    k2.metric("🔋 Total Energi Sesi",   f"{sum(a['energy_kwh'] for a in _ACTIVE):.1f} kWh")
    k3.metric("🔌 Total Daya Aktif",    f"{sum(a['power_kw'] for a in _ACTIVE):.1f} kW")
    st.divider()

    # ── Active charger cards ──────────────────────────────────────────────
    cols_per_row = 2
    rows = [_ACTIVE[i:i+cols_per_row] for i in range(0, len(_ACTIVE), cols_per_row)]
    for row in rows:
        cols = st.columns(cols_per_row, gap="medium")
        for col, ch in zip(cols, row):
            soc_c = "#00d4aa" if ch["soc"]>50 else "#ffd166" if ch["soc"]>20 else "#ff4b6e"
            elapsed = _elapsed(ch["start"])
            with col:
                st.markdown(
                    f"""
                    <div style="background:#1c2333;border:1px solid #2a3348;border-left:3px solid #3a86ff;
                                border-radius:10px;padding:16px 18px;margin-bottom:12px;">
                      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                        <span style="font-size:1.05rem;font-weight:800;">{ch['charger_id']}</span>
                        <span style="background:#3a86ff22;color:#3a86ff;border:1px solid #3a86ff;
                                     border-radius:4px;padding:1px 10px;font-size:0.75rem;font-weight:700;">
                          CHARGING
                        </span>
                      </div>
                      <div style="color:#8892a4;font-size:0.82rem;line-height:2.0;">
                        🏢 <b style="color:#e8eaf6">{ch['station']}</b> – Conn {ch['connector']}<br>
                        🔖 RFID: {ch['id_tag']}<br>
                        🕐 Mulai: {ch['start']}<br>
                        ⏱️ Elapsed: <b style="color:#ffd166">{elapsed}</b>
                      </div>
                      <div style="border-top:1px solid #2a3348;margin:10px 0;"></div>
                      <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:0.85rem;">
                        <div>⚡ Energi: <b style="color:#00d4aa">{ch['energy_kwh']:.2f} kWh</b></div>
                        <div>🔌 Daya: <b style="color:#3a86ff">{ch['power_kw']:.1f} kW</b></div>
                        <div>🔋 Volt: <b style="color:#e8eaf6">{ch['voltage']} V</b></div>
                        <div>🌊 Arus: <b style="color:#e8eaf6">{ch['current']} A</b></div>
                      </div>
                      <div style="margin-top:10px;font-size:0.82rem;">
                        🔋 SoC: <b style="color:{soc_c}">{ch['soc']}%</b>&nbsp;
                        {_soc_bar(ch['soc'])}
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.divider()

    # ── Power distribution chart ──────────────────────────────────────────
    st.markdown("#### 📊 Distribusi Daya Aktif per Charger")
    df_chart = pd.DataFrame(_ACTIVE)
    fig = go.Figure(go.Bar(
        x=df_chart["charger_id"], y=df_chart["power_kw"],
        marker=dict(
            color=df_chart["power_kw"],
            colorscale=[[0,"#1a3d6b"],[1,"#3a86ff"]],
            line=dict(width=0),
        ),
        text=df_chart["power_kw"].apply(lambda v: f"{v:.1f} kW"),
        textposition="outside", textfont=dict(color="#e8eaf6", size=11),
        hovertemplate="%{x}<br>%{y:.1f} kW<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="#0e1117", plot_bgcolor="#1c2333",
        xaxis=dict(gridcolor="#1e2a3a", color="#e8eaf6"),
        yaxis=dict(title="Daya (kW)", gridcolor="#1e2a3a", color="#e8eaf6"),
        font=dict(color="#e8eaf6"), margin=dict(l=40,r=20,t=30,b=40), height=280,
    )
    st.plotly_chart(fig, width="stretch")

    # ── SoC summary ───────────────────────────────────────────────────────
    st.markdown("#### 🔋 State of Charge Kendaraan")
    fig2 = go.Figure()
    for ch in _ACTIVE:
        soc_c = "#00d4aa" if ch["soc"]>50 else "#ffd166" if ch["soc"]>20 else "#ff4b6e"
        fig2.add_trace(go.Bar(
            name=ch["charger_id"], x=[ch["charger_id"]], y=[ch["soc"]],
            marker_color=soc_c,
            text=[f"{ch['soc']}%"], textposition="outside",
            hovertemplate=f"{ch['charger_id']}: {ch['soc']}%<extra></extra>",
        ))
    fig2.add_hline(y=80, line_dash="dash", line_color="#ffd166",
                   annotation_text="80% target", annotation_font=dict(color="#ffd166", size=10))
    fig2.update_layout(
        paper_bgcolor="#0e1117", plot_bgcolor="#1c2333", showlegend=False,
        xaxis=dict(gridcolor="#1e2a3a", color="#e8eaf6"),
        yaxis=dict(title="SoC (%)", range=[0,110], gridcolor="#1e2a3a", color="#e8eaf6"),
        font=dict(color="#e8eaf6"), margin=dict(l=40,r=20,t=30,b=40), height=260,
    )
    st.plotly_chart(fig2, width="stretch")
