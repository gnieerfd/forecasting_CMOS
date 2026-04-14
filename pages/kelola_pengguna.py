"""
pages/kelola_pengguna.py
Kelola Pengguna & Pelanggan – manajemen akun internal dan pelanggan EV.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta

_rng = np.random.default_rng(55)

# ── Mock data ─────────────────────────────────────────────────────────────
_ROLES = ["Superadmin", "Admin", "Operator", "Viewer"]
_STATUSES = ["Aktif", "Nonaktif", "Pending"]

_USERS = pd.DataFrame({
    "id":         range(1, 9),
    "username":   ["setyoajic","admin_bsd","operator1","viewer_ops","admin_ser","oper_bekasi","viewer2","staff_hr"],
    "nama":       ["Setyo Aji C.", "Budi Santoso", "Rini Pratiwi", "Doni S.", "Agus Wijaya", "Sari Dewi", "Wahyu N.", "Hana Putri"],
    "email":      [f"user{i}@cmos.id" for i in range(1, 9)],
    "role":       ["Superadmin","Admin","Operator","Viewer","Admin","Operator","Viewer","Operator"],
    "status":     ["Aktif","Aktif","Aktif","Aktif","Aktif","Nonaktif","Pending","Aktif"],
    "station":    ["All","CS BSD City","CS Serpong","All","CS Serpong","CS Bekasi","All","CS Karawang"],
    "last_login": pd.date_range("2026-04-01", periods=8, freq="12h"),
})

_CUSTOMERS = pd.DataFrame({
    "id":          range(1, 13),
    "nama":        ["Rizky A.","Dewi S.","Budi W.","Anita K.","Fajar R.","Maya L.","Hendra G.","Nia P.","Tommy S.","Lina H.","Agus B.","Citra M."],
    "rfid":        [f"RFID-{1000+i}" for i in range(12)],
    "email":       [f"cust{i}@mail.com" for i in range(12)],
    "telepon":     [f"0812-{_rng.integers(1000,9999)}-{_rng.integers(1000,9999)}" for _ in range(12)],
    "total_sesi":  _rng.integers(1, 120, 12),
    "total_kwh":   _rng.uniform(10, 2500, 12).round(1),
    "status":      _rng.choice(["Aktif","Nonaktif"], 12, p=[0.85,0.15]),
    "registered":  pd.date_range("2025-01-01", periods=12, freq="20D"),
})

_STATUS_COLOR = {"Aktif": "#00d4aa", "Nonaktif": "#ff4b6e", "Pending": "#ffd166"}
_ROLE_COLOR   = {"Superadmin": "#ff6b9d", "Admin": "#3a86ff", "Operator": "#ffd166", "Viewer": "#8892a4"}


def _badge(text: str, color: str) -> str:
    return (f"<span style='background:{color}22;color:{color};border:1px solid {color};"
            f"border-radius:4px;padding:1px 8px;font-size:0.72rem;font-weight:700;'>{text}</span>")


def render_kelola_pengguna() -> None:
    st.markdown(
        "<h1 style='font-size:2rem;font-weight:800;margin-bottom:0.2rem;'>"
        "👥 Kelola Pengguna & Pelanggan</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#8892a4;margin-bottom:1.4rem;'>"
        "Manajemen akun operator/admin internal dan data pelanggan EV terdaftar.</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    tab_user, tab_customer = st.tabs(["👤 Pengguna Internal", "🚗 Pelanggan EV"])

    # ══════════════════════════════════════════════════════════════════════
    # TAB 1 – Pengguna Internal
    # ══════════════════════════════════════════════════════════════════════
    with tab_user:
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("👥 Total Pengguna",  len(_USERS))
        k2.metric("🟢 Aktif",           (_USERS["status"]=="Aktif").sum())
        k3.metric("🔑 Admin",           (_USERS["role"].isin(["Superadmin","Admin"])).sum())
        k4.metric("⚙️ Operator",        (_USERS["role"]=="Operator").sum())
        st.divider()

        # Filter
        fc1, fc2 = st.columns(2)
        filt_role   = fc1.selectbox("Filter Role", ["Semua"]+_ROLES, key="f_role")
        filt_status = fc2.selectbox("Filter Status", ["Semua"]+_STATUSES, key="f_ustat")
        df_u = _USERS.copy()
        if filt_role   != "Semua": df_u = df_u[df_u["role"]   == filt_role]
        if filt_status != "Semua": df_u = df_u[df_u["status"] == filt_status]

        # Table
        st.markdown("##### Daftar Akun")
        for _, row in df_u.iterrows():
            rc = _ROLE_COLOR.get(row["role"], "#aaa")
            sc = _STATUS_COLOR.get(row["status"], "#aaa")
            st.markdown(
                f"""
                <div style="background:#1c2333;border:1px solid #2a3348;border-radius:8px;
                            padding:10px 16px;margin-bottom:6px;display:flex;
                            align-items:center;gap:16px;flex-wrap:wrap;">
                  <span style="font-size:1.6rem;">👤</span>
                  <div style="flex:1;min-width:160px;">
                    <b style="font-size:0.95rem;">{row['nama']}</b>
                    <span style="color:#8892a4;font-size:0.8rem;margin-left:8px;">@{row['username']}</span>
                  </div>
                  <div style="color:#8892a4;font-size:0.8rem;min-width:140px;">{row['email']}</div>
                  <div style="min-width:80px;">{_badge(row['role'], rc)}</div>
                  <div style="min-width:70px;">{_badge(row['status'], sc)}</div>
                  <div style="color:#8892a4;font-size:0.78rem;min-width:120px;">
                    🏢 {row['station']}<br>
                    🕐 {row['last_login'].strftime('%Y-%m-%d %H:%M')}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.divider()
        with st.expander("➕ Tambah Pengguna Baru"):
            nc1, nc2 = st.columns(2)
            nc1.text_input("Nama Lengkap", key="new_u_nama")
            nc2.text_input("Username", key="new_u_user")
            nc3, nc4 = st.columns(2)
            nc3.text_input("Email", key="new_u_email")
            nc4.selectbox("Role", _ROLES, key="new_u_role")
            nc5, nc6 = st.columns(2)
            nc5.text_input("Password", type="password", key="new_u_pw")
            nc6.selectbox("Status", _STATUSES, key="new_u_stat")
            if st.button("💾 Simpan Pengguna", type="primary"):
                st.success("✅ Pengguna berhasil ditambahkan (demo – tidak disimpan ke DB).")

    # ══════════════════════════════════════════════════════════════════════
    # TAB 2 – Pelanggan EV
    # ══════════════════════════════════════════════════════════════════════
    with tab_customer:
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("🚗 Total Pelanggan", len(_CUSTOMERS))
        k2.metric("🟢 Aktif",            (_CUSTOMERS["status"]=="Aktif").sum())
        k3.metric("⚡ Total kWh",        f"{_CUSTOMERS['total_kwh'].sum():,.1f}")
        k4.metric("🔄 Total Sesi",       f"{_CUSTOMERS['total_sesi'].sum():,}")
        st.divider()

        search = st.text_input("🔍 Cari nama / RFID / email pelanggan", key="cust_search")
        df_c = _CUSTOMERS.copy()
        if search:
            mask = (
                df_c["nama"].str.contains(search, case=False) |
                df_c["rfid"].str.contains(search, case=False) |
                df_c["email"].str.contains(search, case=False)
            )
            df_c = df_c[mask]

        for _, row in df_c.iterrows():
            sc = _STATUS_COLOR.get(row["status"], "#aaa")
            st.markdown(
                f"""
                <div style="background:#1c2333;border:1px solid #2a3348;border-radius:8px;
                            padding:10px 16px;margin-bottom:6px;display:flex;
                            align-items:center;gap:14px;flex-wrap:wrap;">
                  <span style="font-size:1.5rem;">🚗</span>
                  <div style="flex:1;min-width:130px;">
                    <b style="font-size:0.93rem;">{row['nama']}</b><br>
                    <span style="color:#8892a4;font-size:0.78rem;">{row['rfid']}</span>
                  </div>
                  <div style="color:#8892a4;font-size:0.8rem;min-width:140px;">
                    {row['email']}<br>{row['telepon']}
                  </div>
                  <div style="font-size:0.8rem;min-width:130px;color:#e8eaf6;">
                    ⚡ {row['total_kwh']:,.1f} kWh<br>
                    🔄 {row['total_sesi']} sesi
                  </div>
                  <div>{_badge(row['status'], sc)}</div>
                  <div style="color:#8892a4;font-size:0.78rem;">
                    📅 {row['registered'].strftime('%Y-%m-%d')}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
