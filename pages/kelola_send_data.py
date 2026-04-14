"""
pages/kelola_send_data.py
Kelola Send Data CS – Kirim perintah OCPP ke Charging Station.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime

_STATIONS = ["CS Serpong", "CS BSD City", "CS Bekasi", "CS Karawang", "CS Depok"]
_CHARGERS = {
    "CS Serpong":   ["CHR-001", "CHR-002", "CHR-003", "CHR-004"],
    "CS BSD City":  ["CHR-005", "CHR-006", "CHR-007"],
    "CS Bekasi":    ["CHR-008", "CHR-009"],
    "CS Karawang":  ["CHR-010"],
    "CS Depok":     [],
}
_COMMANDS = [
    "Reset (Soft)", "Reset (Hard)", "ChangeAvailability – Operative",
    "ChangeAvailability – Inoperative", "TriggerMessage – Heartbeat",
    "TriggerMessage – MeterValues", "TriggerMessage – StatusNotification",
    "UnlockConnector", "SetChargingProfile", "ClearChargingProfile",
    "GetConfiguration", "ChangeConfiguration",
]

# Mock command log stored in session state
_LOG_KEY = "send_data_log"


def _init_log():
    if _LOG_KEY not in st.session_state:
        st.session_state[_LOG_KEY] = pd.DataFrame(columns=[
            "Waktu", "Stasiun", "Charger", "Connector", "Perintah", "Status", "Response"
        ])


def render_kelola_send_data() -> None:
    _init_log()

    st.markdown(
        "<h1 style='font-size:2rem;font-weight:800;margin-bottom:0.2rem;'>"
        "📡 Kelola Send Data CS</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#8892a4;margin-bottom:1.4rem;'>"
        "Kirim perintah OCPP 1.6 ke Charging Station secara remote. "
        "Pastikan charger terhubung ke Central System sebelum mengirim perintah.</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    col_form, col_log = st.columns([1, 1.4], gap="large")

    # ── Left: Command form ────────────────────────────────────────────────
    with col_form:
        st.markdown("#### 📤 Kirim Perintah OCPP")

        sel_station = st.selectbox("🏢 Pilih Stasiun", _STATIONS)
        chargers = _CHARGERS.get(sel_station, [])

        if not chargers:
            st.warning("⚠️ Tidak ada charger terdaftar / stasiun offline.")
            return

        sel_charger   = st.selectbox("🔌 Pilih Charger", chargers)
        sel_connector = st.selectbox("🔢 Connector ID", [1, 2])
        sel_command   = st.selectbox("📋 Perintah OCPP", _COMMANDS)

        # Extra params for some commands
        extra_payload = {}
        if "ChangeConfiguration" in sel_command:
            st.markdown("**Parameter Konfigurasi:**")
            ck1, ck2 = st.columns(2)
            extra_payload["key"]   = ck1.text_input("Key", value="HeartbeatInterval")
            extra_payload["value"] = ck2.text_input("Value", value="30")

        if "SetChargingProfile" in sel_command:
            st.markdown("**Charging Profile:**")
            cp1, cp2 = st.columns(2)
            extra_payload["chargingProfileId"] = cp1.number_input("Profile ID", value=1, min_value=1)
            extra_payload["limit_kw"]           = cp2.number_input("Limit (kW)", value=22.0, min_value=1.0)

        st.markdown("---")
        note = st.text_area("📝 Catatan (opsional)", height=70, placeholder="Alasan pengiriman perintah …")

        send_btn = st.button("🚀 Kirim Perintah", type="primary", use_container_width=True)

        if send_btn:
            import random
            # Simulate response
            success = random.random() > 0.15   # 85% success rate mock
            status   = "✅ Accepted" if success else "❌ Rejected"
            response = (
                '{"status": "Accepted"}' if success
                else '{"status": "Rejected", "reason": "NotSupported"}'
            )
            new_row = pd.DataFrame([{
                "Waktu":     datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Stasiun":   sel_station,
                "Charger":   sel_charger,
                "Connector": sel_connector,
                "Perintah":  sel_command,
                "Status":    status,
                "Response":  response,
            }])
            st.session_state[_LOG_KEY] = pd.concat(
                [new_row, st.session_state[_LOG_KEY]], ignore_index=True
            )
            if success:
                st.success(f"✅ Perintah **{sel_command}** berhasil dikirim ke {sel_charger}.")
            else:
                st.error(f"❌ Perintah ditolak oleh {sel_charger}. Response: {response}")

        # ── OCPP Quick Reference ──────────────────────────────────────────
        with st.expander("📖 Referensi Perintah OCPP 1.6"):
            st.markdown("""
| Perintah | Fungsi |
|---|---|
| **Reset (Soft)** | Restart graceful – tunggu transaksi selesai |
| **Reset (Hard)** | Restart paksa segera |
| **ChangeAvailability** | Ubah status konektor (Operative/Inoperative) |
| **TriggerMessage** | Minta charger kirim pesan tertentu |
| **UnlockConnector** | Buka kunci konektor secara remote |
| **SetChargingProfile** | Atur profil daya pengisian |
| **GetConfiguration** | Baca konfigurasi charger |
| **ChangeConfiguration** | Ubah parameter konfigurasi |
            """)

    # ── Right: Command log ────────────────────────────────────────────────
    with col_log:
        st.markdown("#### 📋 Log Perintah")
        df_log = st.session_state[_LOG_KEY]

        if df_log.empty:
            st.info("Belum ada perintah yang dikirim dalam sesi ini.")
        else:
            # Color-coded status display
            for _, row in df_log.head(20).iterrows():
                is_ok = "Accepted" in row["Status"]
                border_c = "#00d4aa" if is_ok else "#ff4b6e"
                st.markdown(
                    f"""
                    <div style="background:#1c2333;border-left:3px solid {border_c};
                                border-radius:0 8px 8px 0;padding:8px 12px;margin-bottom:6px;
                                border:1px solid #2a3348;border-left:3px solid {border_c};">
                      <div style="display:flex;justify-content:space-between;font-size:0.82rem;">
                        <b>{row['Perintah']}</b>
                        <span style="color:{'#00d4aa' if is_ok else '#ff4b6e'};font-weight:700;">
                          {row['Status']}
                        </span>
                      </div>
                      <div style="color:#8892a4;font-size:0.75rem;margin-top:3px;">
                        🏢 {row['Stasiun']} / {row['Charger']} / Conn {row['Connector']}
                        &nbsp;·&nbsp; 🕐 {row['Waktu']}
                      </div>
                      <code style="font-size:0.72rem;color:#7fe0b0;">{row['Response']}</code>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            if st.button("🗑️ Bersihkan Log", use_container_width=True):
                st.session_state[_LOG_KEY] = pd.DataFrame(columns=df_log.columns)
                st.rerun()
