"""
pages/monitoring_transaction.py
Monitoring Transaction – Live view transaksi aktif + detail meter values per sesi.
Meniru tampilan di screenshot: tabel transaksi, pilih ID, pilih Measurand, grafik, metadata.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta

_rng = np.random.default_rng(33)

# ── Mock measurands ───────────────────────────────────────────────────────
_MEASURANDS = [
    "Energy.Active.Import.Register",
    "Power.Active.Import",
    "Current.Import",
    "Voltage",
    "SoC",
    "Temperature",
    "Current.Offered",
]

# ── Generate mock transactions list ──────────────────────────────────────
def _mock_transactions(n: int = 15) -> pd.DataFrame:
    base_id   = 379
    t_ids     = list(range(base_id + n, base_id, -1))
    conn_ids  = _rng.choice([1, 2], n)
    dates     = pd.date_range("2026-04-08 08:00", periods=n, freq="8h")[::-1]
    return pd.DataFrame({
        "":              range(n),
        "transaction_id": t_ids,
        "connector_id":   conn_ids,
        "start_time":     dates,
    })


# ── Generate mock meter values for a transaction ─────────────────────────
def _mock_meter_values(transaction_id: int, measurand: str) -> pd.DataFrame:
    np.random.seed(transaction_id % 100)
    n = _rng.integers(8, 20)
    t_start = datetime(2026, 4, 10, 8, 0, 0)
    times   = [t_start + timedelta(minutes=5*i) for i in range(n)]

    if measurand == "Energy.Active.Import.Register":
        base  = _rng.uniform(50, 120)
        vals  = base + np.cumsum(np.abs(np.random.normal(5, 2, n)))
    elif measurand == "Power.Active.Import":
        vals  = np.abs(np.random.normal(20, 5, n))
    elif measurand == "Current.Import":
        vals  = np.abs(np.random.normal(32, 4, n))
    elif measurand == "Voltage":
        vals  = np.random.normal(230, 3, n)
    elif measurand == "SoC":
        vals  = np.clip(np.cumsum(np.random.uniform(1, 4, n)) + 20, 0, 100)
    elif measurand == "Temperature":
        vals  = np.random.normal(38, 3, n)
    else:
        vals  = np.abs(np.random.normal(15, 3, n))

    unit_map = {
        "Energy.Active.Import.Register": "Wh",
        "Power.Active.Import": "kW",
        "Current.Import": "A",
        "Voltage": "V",
        "SoC": "%",
        "Temperature": "Celsius",
        "Current.Offered": "A",
    }
    return pd.DataFrame({
        "timestamp": times,
        "measurand": measurand,
        "value":     vals.round(3),
        "unit":      unit_map.get(measurand, ""),
    })


@st.cache_data(show_spinner=False)
def _get_transactions() -> pd.DataFrame:
    return _mock_transactions(15)


def render_monitoring_transaction() -> None:
    st.markdown(
        "<h1 style='font-size:2rem;font-weight:800;margin-bottom:0.2rem;'>"
        "📊 Monitoring Transaction</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#8892a4;margin-bottom:1.4rem;'>"
        "Pantau sesi pengisian aktif, meter values per measurand, dan metadata transaksi secara real-time.</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    df_tx = _get_transactions()

    # ── KPIs ──────────────────────────────────────────────────────────────
    k1, k2, k3 = st.columns(3)
    k1.metric("🔢 Total Transaksi",   len(df_tx))
    k2.metric("⚡ ID Tertinggi",       df_tx["transaction_id"].max())
    k3.metric("🔌 Konektor Aktif",    df_tx["connector_id"].nunique())
    st.divider()

    # ── Recent transaction table ──────────────────────────────────────────
    st.markdown("##### 🗂️ Daftar Transaksi Terbaru")
    df_show = df_tx[["", "transaction_id", "connector_id", "start_time"]].copy()
    df_show["start_time"] = df_show["start_time"].dt.strftime("%Y-%m-%d %H:%M:%S")
    st.dataframe(df_show.head(5), use_container_width=True, hide_index=True, height=220)

    st.divider()

    # ── Detail view ───────────────────────────────────────────────────────
    st.markdown(
        "<span style='font-size:1rem;'>🔵 Lihat detail transaksi:</span>",
        unsafe_allow_html=True,
    )

    t_ids     = df_tx["transaction_id"].tolist()
    sel_tid   = st.selectbox("Transaction ID", t_ids, label_visibility="collapsed")

    tx_row    = df_tx[df_tx["transaction_id"] == sel_tid].iloc[0]

    col_chart, col_meta = st.columns([1.5, 1], gap="large")

    with col_chart:
        # Measurand multiselect (matches screenshot: single choice shown as tag)
        sel_measurands = st.multiselect(
            "Pilih Measurand",
            _MEASURANDS,
            default=["Energy.Active.Import.Register"],
            key="meas_select",
        )

        if not sel_measurands:
            st.info("Pilih minimal satu measurand untuk menampilkan grafik.")
        else:
            fig = go.Figure()
            colors = ["#3a86ff","#00d4aa","#ffd166","#ff6b9d","#a8dadc","#ff9f1c","#e63946"]
            for i, meas in enumerate(sel_measurands):
                df_mv = _mock_meter_values(sel_tid, meas)
                c = colors[i % len(colors)]
                fig.add_trace(go.Scatter(
                    x=df_mv["timestamp"],
                    y=df_mv["value"],
                    name=meas.split(".")[-1] if len(meas) > 20 else meas,
                    mode="lines+markers",
                    line=dict(color=c, width=2),
                    marker=dict(size=5, color=c),
                    hovertemplate=f"%{{x|%H:%M}}<br>{meas}: <b>%{{y:.2f}}</b> {df_mv['unit'].iloc[0]}<extra></extra>",
                ))
            fig.update_layout(
                paper_bgcolor="#0e1117", plot_bgcolor="#1c2333",
                xaxis=dict(title="Waktu", gridcolor="#1e2a3a", color="#e8eaf6"),
                yaxis=dict(title="Nilai", gridcolor="#1e2a3a", color="#e8eaf6"),
                legend=dict(bgcolor="rgba(0,0,0,0.3)", font=dict(size=10)),
                font=dict(color="#e8eaf6"),
                margin=dict(l=50,r=20,t=30,b=50), height=320,
                hovermode="x unified",
            )
            st.plotly_chart(fig, use_container_width=True)

    with col_meta:
        st.markdown(
            "<h3 style='font-size:1.1rem;'>🔍 Metadata</h3>",
            unsafe_allow_html=True,
        )

        # Latest meter value for primary measurand
        primary_meas = sel_measurands[0] if sel_measurands else "Energy.Active.Import.Register"
        df_mv_prime  = _mock_meter_values(sel_tid, primary_meas)
        latest_val   = df_mv_prime["value"].iloc[-1]
        unit         = df_mv_prime["unit"].iloc[0]

        meta_items = [
            ("Measurand",      primary_meas),
            ("Nilai Terakhir", f"{latest_val:.3f} {unit}"),
            ("Connector ID",   tx_row["connector_id"]),
            ("Transaction ID", sel_tid),
            ("Mulai",          tx_row["start_time"].strftime("%Y-%m-%d %H:%M") if hasattr(tx_row["start_time"],"strftime") else str(tx_row["start_time"])),
            ("Total Samples",  len(df_mv_prime)),
        ]
        for label, val in meta_items:
            st.markdown(
                f"""
                <div style="display:flex;justify-content:space-between;
                            border-bottom:1px solid #2a3348;padding:7px 2px;font-size:0.88rem;">
                  <span style="color:#8892a4;">{label}</span>
                  <span style="font-weight:600;color:#e8eaf6;">{val}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # Mini stats
        st.markdown(
            f"""
            <div style="background:#1c2333;border:1px solid #2a3348;border-radius:8px;padding:12px 14px;">
              <div style="color:#8892a4;font-size:0.78rem;margin-bottom:8px;">📈 STATISTIK SESI</div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:0.85rem;">
                <div>Min: <b style="color:#00d4aa">{df_mv_prime['value'].min():.2f}</b></div>
                <div>Max: <b style="color:#ff6b9d">{df_mv_prime['value'].max():.2f}</b></div>
                <div>Avg: <b style="color:#ffd166">{df_mv_prime['value'].mean():.2f}</b></div>
                <div>Std: <b style="color:#3a86ff">{df_mv_prime['value'].std():.2f}</b></div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
