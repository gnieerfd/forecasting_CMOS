"""
pages/laporan_transaksi.py
Laporan Transaksi – ringkasan & export data transaksi pengisian EV.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import io
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta, date

_rng = np.random.default_rng(88)

# ── Generate mock transactions ────────────────────────────────────────────
def _gen_transactions(n: int = 200) -> pd.DataFrame:
    stations   = ["CS Serpong","CS BSD City","CS Bekasi","CS Karawang"]
    connectors = [1, 2]
    id_tags    = [f"RFID-{1000+i}" for i in range(30)]

    start_times = pd.date_range("2026-01-01", periods=n, freq="4h") + pd.to_timedelta(
        _rng.integers(0, 3*3600, n), unit="s"
    )
    durations   = _rng.integers(10*60, 90*60, n)          # seconds
    meter_start = _rng.uniform(0, 50_000, n).round(2)
    energy      = _rng.uniform(3, 60, n).round(3)         # kWh

    return pd.DataFrame({
        "transaction_id": range(200, 200+n),
        "station":        _rng.choice(stations, n),
        "connector_id":   _rng.choice(connectors, n),
        "id_tag":         _rng.choice(id_tags, n),
        "start_time":     start_times,
        "stop_time":      start_times + pd.to_timedelta(durations, unit="s"),
        "duration_min":   (durations / 60).round(1),
        "meter_start_wh": meter_start * 1000,
        "energy_kwh":     energy,
        "cost_idr":       (energy * 2_500).round(0),  # Rp 2.500/kWh mock tariff
        "reason":         _rng.choice(["Local","Remote","EVDisconnected","Other"], n, p=[0.5,0.3,0.15,0.05]),
    })

@st.cache_data(show_spinner=False)
def _load_mock() -> pd.DataFrame:
    return _gen_transactions(200)


def render_laporan_transaksi() -> None:
    st.markdown(
        "<h1 style='font-size:2rem;font-weight:800;margin-bottom:0.2rem;'>"
        "📄 Laporan Transaksi</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#8892a4;margin-bottom:1.4rem;'>"
        "Ringkasan seluruh transaksi pengisian EV – filter, analisis, dan ekspor laporan.</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    df_all = _load_mock()

    # ── Filters ───────────────────────────────────────────────────────────
    fc1, fc2, fc3, fc4 = st.columns(4)
    stations = ["Semua"] + sorted(df_all["station"].unique().tolist())
    sel_st = fc1.selectbox("🏢 Stasiun", stations)

    min_d = df_all["start_time"].dt.date.min()
    max_d = df_all["start_time"].dt.date.max()
    date_from = fc2.date_input("📅 Dari Tanggal", value=max_d - timedelta(days=30), min_value=min_d, max_value=max_d)
    date_to   = fc3.date_input("📅 Sampai", value=max_d, min_value=min_d, max_value=max_d)

    rfid_filter = fc4.text_input("🔖 Filter RFID / ID Tag")

    df = df_all.copy()
    if sel_st != "Semua": df = df[df["station"] == sel_st]
    df = df[(df["start_time"].dt.date >= date_from) & (df["start_time"].dt.date <= date_to)]
    if rfid_filter: df = df[df["id_tag"].str.contains(rfid_filter, case=False)]

    # ── KPIs ──────────────────────────────────────────────────────────────
    st.divider()
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("🔢 Jumlah Transaksi",  f"{len(df):,}")
    k2.metric("⚡ Total Energi",      f"{df['energy_kwh'].sum():,.1f} kWh")
    k3.metric("💰 Total Pendapatan",  f"Rp {df['cost_idr'].sum():,.0f}")
    k4.metric("⏱️ Rata-rata Durasi",  f"{df['duration_min'].mean():.1f} mnt")
    k5.metric("⚡ Avg Energi/Sesi",   f"{df['energy_kwh'].mean():.2f} kWh")
    st.divider()

    # ── Charts row ────────────────────────────────────────────────────────
    ch1, ch2 = st.columns(2, gap="medium")

    with ch1:
        st.markdown("##### 📊 Transaksi Harian")
        daily = df.groupby(df["start_time"].dt.date).agg(
            sesi=("transaction_id","count"), energy=("energy_kwh","sum")
        ).reset_index()
        daily.columns = ["Date","Sesi","Energi_kWh"]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=daily["Date"].astype(str), y=daily["Sesi"],
                             name="Sesi", marker_color="#3a86ff"))
        fig.add_trace(go.Scatter(x=daily["Date"].astype(str), y=daily["Energi_kWh"],
                                 name="Energi (kWh)", yaxis="y2",
                                 line=dict(color="#00d4aa", width=2)))
        fig.update_layout(
            paper_bgcolor="#0e1117", plot_bgcolor="#1c2333",
            xaxis=dict(gridcolor="#1e2a3a", color="#e8eaf6", tickangle=-30),
            yaxis=dict(title="Sesi", gridcolor="#1e2a3a", color="#3a86ff"),
            yaxis2=dict(title="Energi (kWh)", overlaying="y", side="right", color="#00d4aa"),
            legend=dict(bgcolor="rgba(0,0,0,0.3)", font=dict(size=10)),
            font=dict(color="#e8eaf6"), margin=dict(l=50,r=50,t=20,b=60), height=280,
        )
        st.plotly_chart(fig, use_container_width=True)

    with ch2:
        st.markdown("##### 🍩 Energi per Stasiun")
        by_st = df.groupby("station")["energy_kwh"].sum().reset_index()
        fig2 = go.Figure(go.Pie(
            labels=by_st["station"], values=by_st["energy_kwh"], hole=0.5,
            marker=dict(colors=["#00d4aa","#3a86ff","#ffd166","#ff6b9d","#a8dadc"],
                        line=dict(color="#0e1117", width=2)),
            textinfo="label+percent",
            hovertemplate="%{label}<br>%{value:,.1f} kWh<extra></extra>",
        ))
        fig2.update_layout(
            paper_bgcolor="#0e1117", showlegend=False,
            font=dict(color="#e8eaf6"), margin=dict(l=10,r=10,t=20,b=20), height=280,
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # ── Table ─────────────────────────────────────────────────────────────
    st.markdown("##### 📋 Tabel Transaksi")
    df_show = df[["transaction_id","station","connector_id","id_tag",
                  "start_time","stop_time","duration_min","energy_kwh","cost_idr","reason"]].copy()
    df_show["start_time"] = df_show["start_time"].dt.strftime("%Y-%m-%d %H:%M")
    df_show["stop_time"]  = df_show["stop_time"].dt.strftime("%Y-%m-%d %H:%M")
    df_show = df_show.sort_values("transaction_id", ascending=False).reset_index(drop=True)
    st.dataframe(df_show, use_container_width=True, height=320, hide_index=True)

    # ── Export CSV ────────────────────────────────────────────────────────
    st.divider()
    csv_buf = io.StringIO()
    df_show.to_csv(csv_buf, index=False)
    st.download_button(
        label="⬇️ Export CSV",
        data=csv_buf.getvalue(),
        file_name=f"laporan_transaksi_{date_from}_{date_to}.csv",
        mime="text/csv",
        type="primary",
    )
