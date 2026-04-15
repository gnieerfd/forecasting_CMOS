"""
pages/energy_monitoring.py
Real-time Energy Monitoring – CS Serpong
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import streamlit as st
from datetime import date

from components.charts import daily_energy_bar, realtime_energy_line, top5_daily_donut
from services.db_service import fetch_energy_log


def render_energy_monitoring() -> None:
    st.markdown(
        "<h1 style='font-size:2rem;font-weight:800;margin-bottom:0.2rem;'>"
        "Energy Monitoring – CS Serpong</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#8892a4;margin-bottom:1.4rem;'>"
        "Data energi trafo real-time. Auto-refresh dapat diaktifkan di sidebar.</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    # ── Fetch data ────────────────────────────────────────────────────────
    df_raw = fetch_energy_log(station_id="CS_Serpong", limit=500)

    if df_raw.empty:
        st.error("Tidak ada data tersedia.")
        return

    df_raw["Time_Stamp"] = pd.to_datetime(df_raw["Time_Stamp"], errors="coerce")
    df_raw = df_raw.dropna(subset=["Time_Stamp"]).sort_values("Time_Stamp", ascending=False)

    # ── KPI ───────────────────────────────────────────────────────────────
    total_rows    = len(df_raw)
    latest_energy = float(df_raw["Energy_Trafo_2"].iloc[0]) if total_rows > 0 else 0.0

    today    = date.today()
    df_today = df_raw[df_raw["Time_Stamp"].dt.date == today].copy()
    if len(df_today) >= 2:
        total_today = float(df_today["Energy_Trafo_2"].max()
                            - df_today["Energy_Trafo_2"].min())
    else:
        total_today = 0.0

    k1, k2, k3 = st.columns(3)
    k1.metric("Jumlah Data",     f"{total_rows:,}")
    k2.metric("Energi Terakhir", f"{latest_energy:,.2f} kWh")
    k3.metric("Total Hari Ini",  f"{total_today:,.2f} kWh")
    st.divider()

    # ── Data Log Table ────────────────────────────────────────────────────
    st.markdown("### Tabel Data Log")
    df_display = df_raw[["Time_Stamp", "Energy_Trafo_2"]].head(50).copy()
    df_display["Time_Stamp"] = df_display["Time_Stamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    df_display = df_display.rename(columns={"Energy_Trafo_2": "Energy_Trafo_2 (kWh)"})
    st.dataframe(df_display, use_container_width=True, hide_index=False, height=240)
    st.divider()

    # ── Real-time chart ───────────────────────────────────────────────────
    st.markdown("### Grafik Real-time Energy Hari Ini")
    if df_today.empty:
        st.info("Belum ada data untuk hari ini.")
    else:
        df_today_sorted = df_today.sort_values("Time_Stamp")
        st.plotly_chart(realtime_energy_line(df_today_sorted), use_container_width=True)
    st.divider()

    # ── Daily accumulation ────────────────────────────────────────────────
    st.markdown("### Grafik Akumulasi Harian Energy")

    df_asc = df_raw.sort_values("Time_Stamp").copy()
    df_asc["Date"] = df_asc["Time_Stamp"].dt.date

    df_daily = (
        df_asc.groupby("Date")["Energy_Trafo_2"]
        .agg(lambda x: x.max() - x.min())
        .reset_index()
        .rename(columns={"Energy_Trafo_2": "Energy_kWh"})
    )
    df_daily = df_daily[df_daily["Energy_kWh"] > 0]

    if len(df_daily) < 2:
        df_daily = (
            df_asc.groupby("Date")["Energy_Trafo_2"]
            .max()
            .reset_index()
            .rename(columns={"Energy_Trafo_2": "Energy_kWh"})
        )

    ch_left, ch_right = st.columns(2, gap="medium")
    with ch_left:
        if df_daily.empty:
            st.info("Belum ada data akumulasi harian.")
        else:
            st.plotly_chart(daily_energy_bar(df_daily), use_container_width=True)
    with ch_right:
        if len(df_daily) < 2:
            st.info("Minimal 2 hari data untuk donut chart.")
        else:
            st.plotly_chart(top5_daily_donut(df_daily), use_container_width=True)

    st.divider()
    st.caption("Data di-cache 30 detik. Aktifkan Auto-refresh di sidebar untuk update real-time.")