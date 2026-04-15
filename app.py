import sys
import os
import random
import string
from captcha.image import ImageCaptcha

# Pastikan root folder masuk ke path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

st.set_page_config(
    page_title="Charging Station Management System",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* Sembunyikan page list bawaan Streamlit */
    [data-testid="stSidebarNav"] {
        display: none !important;
    }

    .stApp { background-color: #0e1117; }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #161b22 100%);
        border-right: 1px solid #21262d;
    }
    [data-testid="stMetricValue"] { color: #00d4aa !important; font-weight: 700 !important; }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #00d4aa, #0066cc);
        color: white; border: none; border-radius: 8px; font-weight: bold;
    }
    #MainMenu {visibility: hidden;}
    footer    {visibility: hidden;}
    header    {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

import importlib, traceback

_PAGE_MODULES = {
    "Dashboard Lokasi":              ("pages.dashboard_lokasi",       "render_dashboard_lokasi"),
    "Energy Monitoring":             ("pages.energy_monitoring",       "render_energy_monitoring"),
    "Forecasting Zone":              ("pages.forecasting_zone",        "render_forecasting_zone"),
    "Data Rinci Charger":            ("pages.data_rinci_charger",      "render_data_rinci_charger"),
    "Kelola Pengguna dan Pelanggan": ("pages.kelola_pengguna",         "render_kelola_pengguna"),
    "Kelola Send Data CS":           ("pages.kelola_send_data",        "render_kelola_send_data"),
    "Laporan Transaksi":             ("pages.laporan_transaksi",       "render_laporan_transaksi"),
    "Monitoring Transaction":        ("pages.monitoring_transaction",  "render_monitoring_transaction"),
    "Rincian Charger Aktif":         ("pages.rincian_charger_aktif",   "render_rincian_charger_aktif"),
}


def _load_page(page_name: str):
    mod_path, func_name = _PAGE_MODULES[page_name]
    try:
        mod  = importlib.import_module(mod_path)
        func = getattr(mod, func_name)
        return func
    except Exception as e:
        st.error(f" Gagal memuat halaman '{page_name}': {e}")
        with st.expander("Detail Error"):
            st.code(traceback.format_exc())
        return None


# ── SESSION STATE ─────────────────────────────────────────────────────────
if "logged_in"  not in st.session_state: st.session_state["logged_in"]  = False
if "username"   not in st.session_state: st.session_state["username"]   = ""
if "role"       not in st.session_state: st.session_state["role"]       = ""
if "page"       not in st.session_state: st.session_state["page"]       = "Dashboard Lokasi"

_USERS = {
    "ganiarafidah": {"password": "admin123", "role": "Superadmin"},
    "operator":  {"password": "op123",    "role": "Operator"},
}

def generate_new_captcha():
    """Membuat teks CAPTCHA acak (5 karakter huruf kapital & angka)"""
    chars = string.ascii_uppercase + string.digits
    st.session_state["captcha_text"] = ''.join(random.choices(chars, k=5))


def render_login():
    # Pastikan CAPTCHA di-generate saat halaman login pertama kali dibuka
    if "captcha_text" not in st.session_state or not st.session_state["captcha_text"]:
        generate_new_captcha()

    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align:center;background:linear-gradient(135deg,#0d1117,#161b22);
                    border:2px solid #00d4aa;border-radius:16px;padding:30px;
                    box-shadow:0 0 30px rgba(0,212,170,0.15);margin-bottom:24px;">
            <div style="font-size:3rem;">⚡</div>
            <div style="font-size:2.5rem;font-weight:900;color:#00d4aa;letter-spacing:6px;"></div>
            <div style="color:#8892a4;font-size:0.8rem;letter-spacing:2px;margin-top:5px;">
                CHARGING STATION MANAGEMENT SYSTEM
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### Login")
        
        # Generate Gambar CAPTCHA dari Session State
        image_captcha = ImageCaptcha(width=250, height=80)
        captcha_image = image_captcha.generate_image(st.session_state["captcha_text"])

        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Masukkan username")
            password = st.text_input("Password", type="password", placeholder="Masukkan password")
            
            # UI CAPTCHA
            st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
            st.caption("Verifikasi Keamanan:")
            st.image(captcha_image, use_container_width=False)
            captcha_input = st.text_input("Ketik kode di atas", placeholder="Masukkan CAPTCHA")
            
            submit   = st.form_submit_button("Login", use_container_width=True, type="primary")

        if submit:
            user = _USERS.get(username)
            
            # Validasi CAPTCHA terlebih dahulu
            if captcha_input.upper() != st.session_state["captcha_text"]:
                st.error("CAPTCHA salah! Silakan coba lagi.")
                generate_new_captcha() # Reset CAPTCHA
                st.rerun()
                
            # Validasi Akun jika CAPTCHA benar
            elif user and user["password"] == password:
                st.session_state["logged_in"] = True
                st.session_state["username"]  = username
                st.session_state["role"]      = user["role"]
                st.session_state["captcha_text"] = "" # Hapus memori CAPTCHA
                st.success("Login berhasil!")
                st.rerun()
                
            else:
                st.error("Username atau password salah.")
                generate_new_captcha() # Reset CAPTCHA demi keamanan
                st.rerun()


def render_sidebar() -> str:
    with st.sidebar:
        # Logo
        st.markdown("""
        <div style="text-align:center;padding:10px 0 5px 0;">
            <div style="background:linear-gradient(135deg,#0d1117,#161b22);
                        border:2px solid #00d4aa;border-radius:12px;padding:15px;margin-bottom:10px;">
                <span style="font-size:2rem;">⚡</span>
                <div style="font-size:0.6rem;color:#aaa;letter-spacing:1px;">
                    CHARGING MANAGEMENT SYSTEM
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # User info
        uname = st.session_state["username"]
        role  = st.session_state["role"]
        st.markdown(f"""
        <div style="background:#1e4d2b;border:1px solid #2d7a3a;border-radius:8px;
                    padding:10px 14px;margin-bottom:16px;">
            <div style="color:#aaffaa;font-size:0.75rem;">Selamat datang,</div>
            <div style="color:#fff;font-weight:bold;">{uname}</div>
            <div style="color:#88ff88;background:#0d2b16;display:inline-block;
                        padding:2px 8px;border-radius:10px;font-size:0.72rem;margin-top:3px;">
                {role}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Navigasi
        st.markdown("### Navigasi")
        page_options = list(_PAGE_MODULES.keys())
        idx = page_options.index(st.session_state["page"]) \
              if st.session_state["page"] in page_options else 0
        selected = st.selectbox("Pilih Halaman", page_options, index=idx)
        st.session_state["page"] = selected

        st.divider()

        # Auto-refresh khusus Energy Monitoring
        if selected == "Energy Monitoring":
            auto = st.toggle("Auto Refresh (10 detik)", value=False)
            if auto:
                try:
                    from streamlit_autorefresh import st_autorefresh
                    st_autorefresh(interval=10_000, key="energy_refresh")
                except ImportError:
                    st.warning("Install: pip install streamlit-autorefresh")

        # Logout
        if st.button("Logout", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

        st.divider()
    return selected


def main():
    if not st.session_state.get("logged_in"):
        render_login()
        return

    selected = render_sidebar()

    # Render halaman yang dipilih
    render_func = _load_page(selected)
    if render_func:
        try:
            render_func()
        except Exception as e:
            st.error(f"Error saat render halaman: {e}")
            with st.expander("Detail Error"):
                st.code(traceback.format_exc())


if __name__ == "__main__":
    main()