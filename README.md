# ⚡ CMOS – Charging Station Management System

Platform manajemen stasiun pengisian kendaraan listrik berbasis **Streamlit** dengan pipeline ML XGBoost, monitoring real-time, dan integrasi OCPP 1.6.

---

## 📁 Struktur Proyek

```
cmos/
├── app.py                          ← Entry point Streamlit (navigasi sidebar)
├── .streamlit/
│   └── config.toml                 ← Tema gelap + max upload 200 MB
│
├── pages/
│   ├── __init__.py
│   ├── forecasting_zone.py         ← Halaman Energy Demand Forecasting
│   └── energy_monitoring.py        ← Halaman Real-time Energy Monitoring
│
├── components/
│   ├── __init__.py
│   └── charts.py                   ← Builder chart Plotly (dark theme)
│
├── ml_models/
│   ├── __init__.py
│   └── ml_forecasting.py           ← Pipeline XGBoost (feature eng + metrics)
│
└── services/
    ├── __init__.py
    ├── db_service.py               ← SQLAlchemy ORM + mock fallback
    ├── mqtt_service.py             ← paho-mqtt wrapper
    └── ocpp_service.py             ← OCPP 1.6 Central System (asyncio)
```

---

## 🚀 Setup & Menjalankan

### 1. Buat Virtual Environment (Python 3.12.10)

```bash
# Windows
py -3.12 -m venv .venv
.venv\Scripts\activate

# Linux / Mac
python3.12 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements_ocpp.txt
```

> **Catatan OCPP**: Install dari GitHub master (sudah tercantum di requirements_ocpp.txt):
> ```
> git+https://github.com/mobilityhouse/ocpp.git@master
> ```
> Pastikan Git terinstall di sistem Anda.

### 3. Konfigurasi Database (opsional)

Edit variabel environment atau buat file `.env`:

```env
DB_USER=root
DB_PASSWORD=
DB_HOST=localhost
DB_PORT=3306
DB_NAME=cmos_db
```

Jika database tidak tersedia, aplikasi otomatis menggunakan **data mock** (tidak crash).

### 4. Jalankan Aplikasi

```bash
streamlit run app.py
```

Buka browser: `http://localhost:8501`

---

## 📊 Fitur Utama

### Halaman 1: Forecasting Zone
- Upload CSV / XLSX (maks 200 MB)
- Feature engineering otomatis (lag, rolling stats, time features)
- Model **XGBoost Regressor** dengan parameter yang bisa dikonfigurasi
- Metrik evaluasi: **MAPE, MAE, MSE, RMSE, R²**
- Visualisasi interaktif Plotly: historis vs prediksi
- `@st.cache_data` – model tidak di-retrain saat navigasi

### Halaman 2: Energy Monitoring – CS Serpong
- KPI metrics: Jumlah Data, Energi Terakhir, Total Hari Ini
- Tabel Data Log (diurutkan terbaru)
- Grafik real-time energy hari ini
- Bar chart Daily Energy Consumption
- Donut chart Top 5 Daily Energy
- Auto-refresh 10 detik via `streamlit-autorefresh`

---

## 🔧 Layanan Tambahan

### MQTT (Mosquitto)
```bash
# Jalankan Mosquitto broker (XAMPP/standalone)
mosquitto -c mosquitto.conf

# Di Python (background thread)
from services.mqtt_service import CMOSMqttClient
client = CMOSMqttClient(broker="localhost")
client.connect()
client.subscribe("cs/serpong/energy/#")
client.loop_start()
```

### OCPP 1.6 Central System
```bash
# Jalankan sebagai standalone server
python services/ocpp_service.py
# Listens on ws://0.0.0.0:9000
```

---

## 📋 Format Dataset untuk Forecasting

File CSV/XLSX harus memiliki minimal:

| Kolom | Deskripsi |
|-------|-----------|
| `Tanggal` / `Date` / `timestamp` | Kolom tanggal/waktu |
| `Energy Demand EV (kWh)` / kolom numerik pertama | Nilai energi yang akan diprediksi |

Contoh:
```csv
Tanggal,Energy Demand EV (kWh)
2024-01-01,45.3
2024-01-02,52.1
2024-01-03,48.7
```

---

## ⚙️ Konfigurasi Tema

File `.streamlit/config.toml` sudah dikonfigurasi dengan tema gelap CMOS.
Warna utama: `#00d4aa` (teal), background: `#0e1117`.
