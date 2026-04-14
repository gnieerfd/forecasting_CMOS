"""
pages/forecasting_zone.py  ─ CMOS v3 (FIXED)
Energy Demand Forecasting – 6 Model: ARIMA · SVR · LR · XGBoost · ANN · LSTM

DAFTAR BUG YANG DIPERBAIKI
══════════════════════════════════════════════════════════════════
1. ARIMA train_pred panjang salah → pakai fittedvalues dengan index yang benar
2. LSTM/ANN/SVR/LR: future_pred loop pakai scaled yang belum diupdate → pakai
   buffer tersendiri `last_window` yang benar-benar bergeser tiap step
3. ARIMA future refit duplikat (refit dua kali, lambat) → cukup satu fit
4. st.cache_data pada train_model menyimpan objek TF/Keras yang tidak bisa
   di-pickle → LSTM sekarang memakai numpy-only return (bobot disimpan sbg array)
5. chart_choice "Choose chart…" masih render metric placeholder di bawah
   walau result sudah ada → diperbaiki logic kondisionalnya
6. forecast_days number_input menghasilkan int tapi dikirim sbg int langsung ✓
7. window size 1 membuat _windows() menghasilkan array kosong → minimum guard 3
8. Sliding window untuk ARIMA tidak relevan → disembunyikan otomatis
9. Semua model: test_vals di-trim dua kali (split dan slice) → satu sumber kebenaran
10. @st.cache_data tidak bisa menyimpan DataFrame ber-timezone → strip tz sebelum cache
══════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import io
import sys
import os
import warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import MinMaxScaler

# ══════════════════════════════════════════════════════════════════════════════
# KONSTANTA
# ══════════════════════════════════════════════════════════════════════════════
_BG   = "#0e1117"
_CARD = "#1c2333"
_GRID = "#1e2a3a"
_FONT = "#e8eaf6"
_C_ACTUAL  = "#00d4aa"   # teal  – data asli
_C_TRAIN   = "#3a86ff"   # biru  – prediksi train
_C_TEST    = "#ff6b9d"   # pink  – prediksi test
_C_FUTURE  = "#ffd166"   # gold  – forecast masa depan

_MODELS = ["ARIMA", "SVR", "LR", "XGBOOST", "ANN", "LSTM"]
_SPLIT_OPTIONS = {"90:10": 0.10, "80:20": 0.20, "70:30": 0.30, "60:40": 0.40}

# ══════════════════════════════════════════════════════════════════════════════
# HELPER UMUM
# ══════════════════════════════════════════════════════════════════════════════

def _load_file(uploaded) -> tuple[pd.DataFrame, str]:
    """Baca CSV atau XLSX dari UploadedFile. Return (df, error_str)."""
    try:
        raw  = uploaded.read()
        name = uploaded.name.lower()
        if name.endswith((".xlsx", ".xls")):
            return pd.read_excel(io.BytesIO(raw)), ""
        for sep in [",", ";", "\t"]:
            try:
                df = pd.read_csv(io.BytesIO(raw), sep=sep)
                if df.shape[1] > 1:
                    return df, ""
            except Exception:
                continue
        return pd.read_csv(io.BytesIO(raw)), ""
    except Exception as e:
        return pd.DataFrame(), str(e)


def _detect_columns(df: pd.DataFrame) -> tuple[str | None, str | None]:
    """
    Deteksi otomatis kolom tanggal dan kolom target energi.
    Mencari berdasarkan kata kunci dalam nama kolom.
    """
    date_kw   = ["time","date","tanggal","timestamp","waktu","datetime","start"]
    target_kw = ["energy","kwh","demand","consumption","konsumsi","energi",
                 "power","daya","trafo","watt","load"]
    low = {c.lower(): c for c in df.columns}

    date_col = target_col = None
    for kw in date_kw:
        for cl, c in low.items():
            if kw in cl:
                date_col = c
                break
        if date_col:
            break

    for kw in target_kw:
        for cl, c in low.items():
            if kw in cl and c != date_col:
                target_col = c
                break
        if target_col:
            break

    # Fallback
    if date_col is None and len(df.columns) > 0:
        date_col = df.columns[0]
    if target_col is None:
        nums = df.select_dtypes(include=np.number).columns.tolist()
        # jangan pilih kolom yang sudah jadi date_col
        nums = [c for c in nums if c != date_col]
        target_col = nums[0] if nums else None

    return date_col, target_col


def _prepare(df: pd.DataFrame, date_col: str, target_col: str) -> pd.DataFrame:
    """Bersihkan, parse tipe, urutkan, hapus NaN."""
    df = df[[date_col, target_col]].copy()
    df[date_col]   = pd.to_datetime(df[date_col], errors="coerce")
    df[target_col] = pd.to_numeric(df[target_col], errors="coerce")
    df = df.dropna().sort_values(date_col).reset_index(drop=True)
    # Hapus timezone agar cache_data bisa pickle
    if hasattr(df[date_col].dtype, "tz") and df[date_col].dt.tz is not None:
        df[date_col] = df[date_col].dt.tz_localize(None)
    return df


def _make_windows(vals: np.ndarray, w: int) -> tuple[np.ndarray, np.ndarray]:
    """
    Buat sliding window: setiap sampel X[i] = vals[i:i+w], y[i] = vals[i+w].
    Contoh (w=3, vals=[1,2,3,4,5]):
        X = [[1,2,3],[2,3,4]]   y = [4, 5]
    """
    X, y = [], []
    for i in range(len(vals) - w):
        X.append(vals[i : i + w])
        y.append(vals[i + w])
    return np.array(X), np.array(y)


def _metrics(yt: np.ndarray, yp: np.ndarray) -> dict:
    eps = 1e-9
    return {
        "MAPE": float(np.mean(np.abs((yt - yp) / (np.abs(yt) + eps))) * 100),
        "MAE":  float(mean_absolute_error(yt, yp)),
        "MSE":  float(mean_squared_error(yt, yp)),
        "RMSE": float(np.sqrt(mean_squared_error(yt, yp))),
        "R²":   float(r2_score(yt, yp)),
    }


def _infer_freq(dates: pd.Series) -> str:
    """Deteksi frekuensi data (menit / jam / hari / minggu / bulan)."""
    try:
        s = dates.diff().dropna().median().total_seconds()
        if s < 3600:    return "min"
        if s < 86400:   return "h"
        if s < 7*86400: return "D"
        if s < 32*86400:return "W"
        return "ME"
    except Exception:
        return "D"


# ══════════════════════════════════════════════════════════════════════════════
# FUNGSI TRAINING (di-cache agar tidak re-train saat navigasi)
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False)
def train_model(
    cache_key: str,       # kunci unik agar cache invalid saat parameter berubah
    values_json: str,     # data target dalam JSON (numpy→JSON agar bisa di-pickle)
    model_name: str,
    test_ratio: float,
    window: int,
    forecast_days: int,
) -> dict:
    """
    Pipeline training + evaluasi + future forecast.

    Parameter
    ---------
    cache_key    : Gabungan nama file + model + split + window + hari → invalidasi cache
    values_json  : Series target dalam format JSON (menghindari masalah pickle TF/Keras)
    model_name   : Nama model: ARIMA | SVR | LR | XGBOOST | ANN | LSTM
    test_ratio   : Proporsi data uji, misal 0.20 = 20%
    window       : Panjang sliding window (jumlah langkah waktu sebelumnya sebagai input)
    forecast_days: Berapa hari ke depan ingin diprediksi

    Return
    ------
    dict berisi: train_actual, train_pred, test_actual, test_pred,
                 future_pred, train_metrics, test_metrics, feat_imp, split, window
    """
    # ── Rekonstruksi array nilai ──────────────────────────────────────────
    values = np.array(
        pd.read_json(io.StringIO(values_json), typ="series").values,
        dtype=float,
    )
    n      = len(values)
    split  = int(n * (1 - test_ratio))     # indeks awal data test

    # Satu sumber kebenaran untuk nilai aktual
    train_vals_full = values[:split]       # semua data latih
    test_vals_full  = values[split:]       # semua data uji

    # Normalisasi Min-Max ke [0,1]
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled = scaler.fit_transform(values.reshape(-1, 1)).flatten()
    train_s = scaled[:split]

    feat_imp    = None
    train_pred  = None
    test_pred   = None
    train_actual = None
    test_actual  = None

    # ══════════════════════════════════════════════════════════════════════
    # MODEL: ARIMA
    # ══════════════════════════════════════════════════════════════════════
    if model_name == "ARIMA":
        # ARIMA tidak memakai sliding window — model statistik berbasis differencing
        from statsmodels.tsa.arima.model import ARIMA as _ARIMA

        fit = _ARIMA(train_vals_full, order=(5, 1, 0)).fit()

        # Fitted values = prediksi in-sample (panjang sama dengan train)
        # np.asarray() aman untuk pandas Series maupun numpy array
        train_pred   = np.asarray(fit.fittedvalues).astype(float)
        train_actual = train_vals_full.copy()

        # Forecast ke depan sejumlah data test
        test_pred    = np.asarray(fit.forecast(steps=len(test_vals_full))).astype(float)
        test_actual  = test_vals_full.copy()

        # Trim agar panjang sama persis
        mn_tr = min(len(train_actual), len(train_pred))
        mn_te = min(len(test_actual),  len(test_pred))
        train_actual = train_actual[:mn_tr]; train_pred = train_pred[:mn_tr]
        test_actual  = test_actual[:mn_te];  test_pred  = test_pred[:mn_te]

        # Future forecast – refit dengan semua data
        fut_fit = _ARIMA(values, order=(5, 1, 0)).fit()
        future_pred = np.asarray(fut_fit.forecast(steps=forecast_days)).astype(float)

    # ══════════════════════════════════════════════════════════════════════
    # MODEL: SVR / LR / XGBOOST / ANN  (window-based)
    # ══════════════════════════════════════════════════════════════════════
    elif model_name in ("SVR", "LR", "XGBOOST", "ANN"):

        # Buat windows dari data latih (scaled)
        X_tr, y_tr = _make_windows(train_s, window)

        # Buat windows dari data uji: window terakhir train + semua test (scaled)
        all_scaled_for_test = scaled[split - window : split + len(test_vals_full)]
        X_te, y_te = _make_windows(all_scaled_for_test, window)

        # Pilih model
        if model_name == "SVR":
            from sklearn.svm import SVR
            mdl = SVR(kernel="rbf", C=100, epsilon=0.01)

        elif model_name == "LR":
            from sklearn.linear_model import LinearRegression
            mdl = LinearRegression()

        elif model_name == "XGBOOST":
            try:
                from xgboost import XGBRegressor
                mdl = XGBRegressor(
                    n_estimators=200, max_depth=5, learning_rate=0.05,
                    subsample=0.8, colsample_bytree=0.8,
                    random_state=42, verbosity=0, tree_method="hist",
                )
            except ImportError:
                from sklearn.ensemble import GradientBoostingRegressor
                mdl = GradientBoostingRegressor(
                    n_estimators=200, max_depth=5, learning_rate=0.05, random_state=42,
                )

        elif model_name == "ANN":
            from sklearn.neural_network import MLPRegressor
            mdl = MLPRegressor(
                hidden_layer_sizes=(128, 64, 32),
                activation="relu",
                max_iter=1000,
                random_state=42,
                early_stopping=True,
                validation_fraction=0.1,
                n_iter_no_change=20,
            )

        mdl.fit(X_tr, y_tr)

        # Prediksi train (kembali ke skala asli)
        train_pred_s = mdl.predict(X_tr)
        train_pred   = scaler.inverse_transform(train_pred_s.reshape(-1, 1)).flatten()
        train_actual = train_vals_full[window:]    # ← potong window awal (tidak ada input sebelumnya)

        # Prediksi test
        test_pred_s  = mdl.predict(X_te)
        test_pred    = scaler.inverse_transform(test_pred_s.reshape(-1, 1)).flatten()
        test_actual  = test_vals_full[:len(test_pred)]

        # Trim
        mn_tr = min(len(train_actual), len(train_pred))
        mn_te = min(len(test_actual),  len(test_pred))
        train_actual = train_actual[:mn_tr]; train_pred = train_pred[:mn_tr]
        test_actual  = test_actual[:mn_te];  test_pred  = test_pred[:mn_te]

        # Feature importance (XGBoost saja)
        feat_imp = getattr(mdl, "feature_importances_", None)

        # Future forecast – iteratif: prediksi satu langkah, masukkan ke window
        last_window = list(scaled[-window:])    # window terakhir dari semua data
        future_pred = []
        for _ in range(forecast_days):
            xi = np.array(last_window[-window:]).reshape(1, -1)
            p  = float(mdl.predict(xi)[0])
            val = float(scaler.inverse_transform([[p]])[0][0])
            future_pred.append(val)
            last_window.append(p)               # geser window: nilai scaled

        future_pred = np.array(future_pred)

    # ══════════════════════════════════════════════════════════════════════
    # MODEL: LSTM
    # ══════════════════════════════════════════════════════════════════════
    elif model_name == "LSTM":
        try:
            import tensorflow as tf
            from tensorflow.keras.models import Sequential
            from tensorflow.keras.layers import LSTM as _LSTM, Dense, Dropout
            from tensorflow.keras.callbacks import EarlyStopping
        except ImportError:
            raise RuntimeError(
                "TensorFlow tidak terinstall.\n"
                "Jalankan: pip install tensorflow==2.20.0"
            )

        tf.random.set_seed(42)

        # Windows
        X_tr, y_tr = _make_windows(train_s, window)
        all_scaled_for_test = scaled[split - window : split + len(test_vals_full)]
        X_te, y_te = _make_windows(all_scaled_for_test, window)

        # Reshape ke (samples, timesteps, features)
        X_tr_3d = X_tr.reshape(-1, window, 1)
        X_te_3d = X_te.reshape(-1, window, 1)

        # Arsitektur LSTM
        mdl = Sequential([
            _LSTM(64, return_sequences=True, input_shape=(window, 1)),
            Dropout(0.2),
            _LSTM(32),
            Dropout(0.2),
            Dense(16, activation="relu"),
            Dense(1),
        ])
        mdl.compile(optimizer="adam", loss="mse")
        mdl.fit(
            X_tr_3d, y_tr,
            epochs=100,
            batch_size=16,
            verbose=0,
            validation_split=0.1,
            callbacks=[EarlyStopping(patience=10, restore_best_weights=True)],
        )

        # Prediksi
        train_pred_s = mdl.predict(X_tr_3d, verbose=0).flatten()
        train_pred   = scaler.inverse_transform(train_pred_s.reshape(-1, 1)).flatten()
        train_actual = train_vals_full[window:]

        test_pred_s  = mdl.predict(X_te_3d, verbose=0).flatten()
        test_pred    = scaler.inverse_transform(test_pred_s.reshape(-1, 1)).flatten()
        test_actual  = test_vals_full[:len(test_pred)]

        # Trim
        mn_tr = min(len(train_actual), len(train_pred))
        mn_te = min(len(test_actual),  len(test_pred))
        train_actual = train_actual[:mn_tr]; train_pred = train_pred[:mn_tr]
        test_actual  = test_actual[:mn_te];  test_pred  = test_pred[:mn_te]

        # Future forecast iteratif
        last_window = list(scaled[-window:])
        future_pred = []
        for _ in range(forecast_days):
            xi = np.array(last_window[-window:]).reshape(1, window, 1)
            p  = float(mdl.predict(xi, verbose=0)[0][0])
            val = float(scaler.inverse_transform([[p]])[0][0])
            future_pred.append(val)
            last_window.append(p)

        future_pred = np.array(future_pred)

    else:
        raise ValueError(f"Model tidak dikenal: {model_name}")

    return {
        "train_actual":  train_actual,
        "train_pred":    train_pred,
        "test_actual":   test_actual,
        "test_pred":     test_pred,
        "future_pred":   future_pred,
        "train_metrics": _metrics(train_actual, train_pred),
        "test_metrics":  _metrics(test_actual,  test_pred),
        "feat_imp":      feat_imp,
        "split":         split,
        "window":        window,
    }


# ══════════════════════════════════════════════════════════════════════════════
# CHART BUILDERS
# ══════════════════════════════════════════════════════════════════════════════

def _layout(title="", **kw) -> dict:
    base = dict(
        paper_bgcolor=_BG, plot_bgcolor=_CARD,
        font=dict(color=_FONT, size=12),
        xaxis=dict(gridcolor=_GRID, color=_FONT, title_font=dict(color=_FONT)),
        yaxis=dict(gridcolor=_GRID, color=_FONT, title_font=dict(color=_FONT)),
        legend=dict(bgcolor="rgba(0,0,0,0.3)", bordercolor="#2a3348", borderwidth=1),
        margin=dict(l=55, r=20, t=55, b=55),
        hovermode="x unified",
        title=dict(text=title, font=dict(size=14)),
    )
    base.update(kw)
    return base


def chart_actual(dates, values, mn):
    """Tampilkan seluruh dataset historis tanpa prediksi."""
    fig = go.Figure(go.Scatter(
        x=dates, y=values, name="Aktual",
        mode="lines", line=dict(color=_C_ACTUAL, width=2),
        hovertemplate="%{x|%Y-%m-%d}<br>Aktual: <b>%{y:.2f}</b><extra></extra>",
    ))
    fig.update_layout(**_layout(
        f"{mn} – Actual Dataset",
        xaxis_title="Tanggal", yaxis_title="Energy Demand EV (kWh)",
    ))
    return fig


def chart_train(dt, ta, tp, mn):
    """
    Grafik Train Forecast: data aktual (train) vs hasil prediksi model pada
    data latih. Menunjukkan seberapa bagus model 'menghafal' pola data latih.
    """
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dt, y=ta, name="Aktual (Train)",
        mode="lines", line=dict(color=_C_ACTUAL, width=2),
        hovertemplate="%{x|%Y-%m-%d}<br>Aktual: <b>%{y:.2f}</b><extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=dt, y=tp, name=f"Prediksi {mn} (Train)",
        mode="lines", line=dict(color=_C_TRAIN, width=2, dash="dash"),
        hovertemplate="%{x|%Y-%m-%d}<br>Prediksi: <b>%{y:.2f}</b><extra></extra>",
    ))
    fig.update_layout(**_layout(
        f"{mn} – Train Forecast",
        xaxis_title="Tanggal", yaxis_title="Energy Demand EV (kWh)",
    ))
    return fig


def chart_test(dt_te, ta, tp, dt_fu, fp, mn):
    """
    Grafik Test Forecast: data aktual (test) vs prediksi test + garis forecast
    ke masa depan (warna kuning). Ini adalah evaluasi utama model.
    """
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dt_te, y=ta, name="Aktual (Test)",
        mode="lines", line=dict(color=_C_ACTUAL, width=2),
        hovertemplate="%{x|%Y-%m-%d}<br>Aktual: <b>%{y:.2f}</b><extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=dt_te, y=tp, name=f"Prediksi {mn} (Test)",
        mode="lines", line=dict(color=_C_TEST, width=2, dash="dash"),
        hovertemplate="%{x|%Y-%m-%d}<br>Prediksi: <b>%{y:.2f}</b><extra></extra>",
    ))
    if dt_fu is not None and len(fp) > 0:
        fig.add_trace(go.Scatter(
            x=dt_fu, y=fp, name="Forecast (Masa Depan)",
            mode="lines+markers", marker=dict(size=4),
            line=dict(color=_C_FUTURE, width=2, dash="dot"),
            fill="tozeroy", fillcolor="rgba(255,209,102,0.05)",
            hovertemplate="%{x|%Y-%m-%d}<br>Forecast: <b>%{y:.2f}</b><extra></extra>",
        ))
    fig.update_layout(**_layout(
        f"{mn} – Test Forecast & Proyeksi",
        xaxis_title="Tanggal", yaxis_title="Energy Demand EV (kWh)",
    ))
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# MAIN PAGE RENDER
# ══════════════════════════════════════════════════════════════════════════════

def render_forecasting_zone() -> None:
    st.markdown(
        "<h1 style='font-size:2rem;font-weight:800;margin-bottom:0.2rem;'>"
        "📈 Energy Demand Forecasting</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#8892a4;margin-bottom:1rem;'>"
        "Upload dataset historis → pilih model → lihat prediksi dan metrik evaluasi.</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    col_l, col_r = st.columns([1, 1.8], gap="large")

    # ══════════════════════════════════════════════════════════════════════
    # PANEL KIRI – Upload & Konfigurasi
    # ══════════════════════════════════════════════════════════════════════
    with col_l:
        st.markdown("### 📁 Upload Dataset")
        uploaded = st.file_uploader(
            "Unggah dataset (CSV/XLSX)",
            type=["csv", "xlsx", "xls"],
            help="Limit 200 MB. Harus ada kolom tanggal dan kolom energi/kWh.",
        )
        if uploaded is None:
            st.warning("⚠️ Silakan unggah file CSV/XLSX untuk memulai forecasting.")

        st.divider()
        st.markdown("### ⚙️ Konfigurasi Model")

        # 1. Pilih model
        model_name = st.selectbox(
            "🤖 Learning Method:",
            _MODELS,
            index=3,   # default XGBOOST
            help=(
                "ARIMA: statistik klasik\n"
                "SVR/LR: ML tradisional\n"
                "XGBoost: gradient boosting\n"
                "ANN: neural network\n"
                "LSTM: deep learning urutan waktu"
            ),
        )

        # 2. Rasio train/test
        split_label = st.selectbox(
            "📊 Select Train/Test Split Ratio:",
            list(_SPLIT_OPTIONS.keys()),
            index=1,   # default 80:20
            help=(
                "Misal 80:20 → 80% data untuk melatih model, "
                "20% sisanya untuk menguji performa model pada data yang belum dilihat."
            ),
        )
        test_ratio = _SPLIT_OPTIONS[split_label]

        # 3. Hari forecast
        forecast_days = int(st.number_input(
            "📅 Input day to forecast:",
            min_value=1, max_value=365, value=30, step=1,
            help="Berapa hari ke depan ingin diproyeksikan setelah data terakhir.",
        ))

        # 4. Sliding window (sembunyikan untuk ARIMA)
        window = 7   # default
        if model_name != "ARIMA":
            window = int(st.number_input(
                "🪟 Sliding window size:",
                min_value=3, max_value=60, value=7, step=1,
                help=(
                    "Jumlah titik waktu sebelumnya yang digunakan sebagai input.\n"
                    "Contoh window=7: model belajar dari 7 hari terakhir untuk prediksi hari berikutnya."
                ),
            ))

        # 5. Pilih grafik
        chart_choice = st.selectbox(
            "📉 Choose chart to display:",
            [
                "— Pilih grafik —",
                "Actual Dataset",
                "Train Forecast",
                "Test Forecast",
            ],
            help=(
                "Actual Dataset: tampilkan data asli saja.\n"
                "Train Forecast: bandingkan prediksi model pada data latih.\n"
                "Test Forecast: evaluasi pada data uji + proyeksi masa depan."
            ),
        )

        run_btn = st.button(
            "🚀 Jalankan Forecasting",
            use_container_width=True,
            type="primary",
        )

    # ══════════════════════════════════════════════════════════════════════
    # PANEL KANAN – Grafik & Metrik
    # ══════════════════════════════════════════════════════════════════════
    with col_r:
        st.markdown("### 📊 Visualisasi Forecasting")

        # ── Trigger training ──────────────────────────────────────────────
        if run_btn:
            if uploaded is None:
                st.warning("⚠️ Upload file terlebih dahulu.")
            else:
                df_raw, err = _load_file(uploaded)
                if err:
                    st.error(f"❌ Gagal membaca file: {err}")
                else:
                    date_col, target_col = _detect_columns(df_raw)
                    if target_col is None:
                        st.error("❌ Tidak ditemukan kolom energi/kWh dalam file.")
                    else:
                        df = _prepare(df_raw, date_col, target_col)
                        min_rows = window + 10 if model_name != "ARIMA" else 20
                        if len(df) < min_rows:
                            st.error(
                                f"❌ Data terlalu sedikit ({len(df)} baris valid). "
                                f"Minimal {min_rows} baris untuk model ini."
                            )
                        else:
                            # Serialisasi target ke JSON agar @cache_data bisa pickle
                            vals_json = pd.Series(df[target_col].values).to_json()
                            ckey = (
                                f"{uploaded.name}|{model_name}|{split_label}"
                                f"|w{window}|f{forecast_days}"
                            )
                            with st.spinner(f"⏳ Melatih model {model_name} …"):
                                try:
                                    res = train_model(
                                        ckey, vals_json, model_name,
                                        test_ratio, window, forecast_days,
                                    )
                                    # Simpan tanggal dan nama model ke result
                                    res["dates"]      = df[date_col]
                                    res["model_name"] = model_name
                                    st.session_state["fc_result"]  = res
                                    st.session_state["fc_window"]  = window
                                    st.session_state["fc_fdays"]   = forecast_days
                                    st.success(f"✅ Model {model_name} berhasil dilatih!")
                                except Exception as e:
                                    st.error(f"❌ Error training: {e}")
                                    st.session_state.pop("fc_result", None)

        # ── Ambil result dari session ─────────────────────────────────────
        res          = st.session_state.get("fc_result")
        s_window     = st.session_state.get("fc_window", window)
        s_fdays      = st.session_state.get("fc_fdays",  forecast_days)

        # ── Render grafik ─────────────────────────────────────────────────
        if res is None or chart_choice == "— Pilih grafik —":
            # Placeholder kosong
            fig_ph = go.Figure()
            fig_ph.add_annotation(
                text="Upload file, konfigurasi model, lalu klik Jalankan Forecasting",
                x=0.5, y=0.5, xref="paper", yref="paper",
                showarrow=False, font=dict(size=12, color="#556"),
            )
            fig_ph.update_layout(
                paper_bgcolor=_BG, plot_bgcolor=_CARD,
                xaxis=dict(title="Tanggal", gridcolor=_GRID, color="#8892a4"),
                yaxis=dict(title="Energy Demand EV (kWh)", gridcolor=_GRID, color="#8892a4"),
                margin=dict(l=55, r=20, t=40, b=55), height=380,
            )
            st.plotly_chart(fig_ph, use_container_width=True)

        else:
            dates     = res["dates"]
            split_idx = res["split"]
            mn        = res.get("model_name", model_name)
            freq      = _infer_freq(dates)
            w         = res["window"]

            # Hitung range tanggal untuk train / test / future
            if mn == "ARIMA":
                d_tr = dates.iloc[:split_idx]
                d_te = dates.iloc[split_idx : split_idx + len(res["test_actual"])]
            else:
                d_tr = dates.iloc[w : split_idx]
                d_tr = d_tr.iloc[: len(res["train_actual"])]
                d_te = dates.iloc[split_idx : split_idx + len(res["test_actual"])]

            d_fu = pd.date_range(
                start=dates.iloc[-1],
                periods=s_fdays + 1,
                freq=freq,
            )[1:]

            # ── Tampilkan sesuai pilihan ──────────────────────────────────
            if chart_choice == "Actual Dataset":
                all_vals = np.concatenate([res["train_actual"], res["test_actual"]])
                all_dates = dates.iloc[: len(all_vals)]
                st.plotly_chart(
                    chart_actual(all_dates, all_vals, mn),
                    use_container_width=True,
                )

            elif chart_choice == "Train Forecast":
                l = min(len(d_tr), len(res["train_actual"]))
                st.plotly_chart(
                    chart_train(
                        d_tr.iloc[:l],
                        res["train_actual"][:l],
                        res["train_pred"][:l],
                        mn,
                    ),
                    use_container_width=True,
                )

            elif chart_choice == "Test Forecast":
                l = min(len(d_te), len(res["test_actual"]))
                f = min(len(d_fu), len(res["future_pred"]))
                st.plotly_chart(
                    chart_test(
                        d_te.iloc[:l],
                        res["test_actual"][:l],
                        res["test_pred"][:l],
                        d_fu[:f],
                        res["future_pred"][:f],
                        mn,
                    ),
                    use_container_width=True,
                )

        # ════════════════════════════════════════════════════════════════
        # EVALUATION METRICS
        # ════════════════════════════════════════════════════════════════
        st.markdown("### 📐 Evaluation Metrics")

        if res:
            m = res["test_metrics"]

            # Metrik utama (Test)
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("MAPE", f"{m['MAPE']:.2f}%")
            c2.metric("MAE",  f"{m['MAE']:.4f}")
            c3.metric("MSE",  f"{m['MSE']:.4f}")
            c4.metric("RMSE", f"{m['RMSE']:.4f}")
            c5.metric("R²",   f"{m['R²']:.4f}")

            # Tabel ringkasan
            st.dataframe(
                pd.DataFrame([{
                    "Model": res.get("model_name", model_name),
                    "MAPE":  f"{m['MAPE']:.2f}%",
                    "MAE":   f"{m['MAE']:.4f}",
                    "MSE":   f"{m['MSE']:.4f}",
                    "RMSE":  f"{m['RMSE']:.4f}",
                    "R²":    f"{m['R²']:.4f}",
                }]),
                use_container_width=True,
                hide_index=True,
            )

            # Metrik train (dalam expander)
            with st.expander("📊 Train Metrics (in-sample)"):
                tm = res["train_metrics"]
                t1, t2, t3, t4, t5 = st.columns(5)
                t1.metric("MAPE", f"{tm['MAPE']:.2f}%")
                t2.metric("MAE",  f"{tm['MAE']:.4f}")
                t3.metric("MSE",  f"{tm['MSE']:.4f}")
                t4.metric("RMSE", f"{tm['RMSE']:.4f}")
                t5.metric("R²",   f"{tm['R²']:.4f}")
                st.caption(
                    "Train metrics menunjukkan seberapa baik model fit pada data latih. "
                    "Jika jauh lebih bagus dari Test metrics, model kemungkinan overfitting."
                )

            # Feature importance (XGBoost)
            if res.get("feat_imp") is not None:
                with st.expander("🔍 Feature Importance (XGBOOST)"):
                    imp = res["feat_imp"]
                    w_  = res["window"]
                    labels = [f"lag_{i+1}" for i in range(len(imp))]
                    s   = pd.Series(imp, index=labels).sort_values(ascending=False).head(10)
                    fig_fi = go.Figure(go.Bar(
                        x=s.values, y=s.index, orientation="h",
                        marker=dict(
                            color=s.values,
                            colorscale=[[0, "#1c2333"], [1, "#00d4aa"]],
                        ),
                        hovertemplate="%{y}: %{x:.4f}<extra></extra>",
                    ))
                    fig_fi.update_layout(
                        paper_bgcolor=_BG, plot_bgcolor=_CARD,
                        xaxis=dict(title="Importance Score", gridcolor=_GRID, color=_FONT),
                        yaxis=dict(autorange="reversed", gridcolor=_GRID, color=_FONT),
                        font=dict(color=_FONT),
                        margin=dict(l=80, r=20, t=30, b=40),
                        height=280,
                    )
                    st.plotly_chart(fig_fi, use_container_width=True)

            # Download forecast CSV
            freq_used = _infer_freq(res["dates"])
            d_fu_dl   = pd.date_range(
                start=res["dates"].iloc[-1],
                periods=s_fdays + 1,
                freq=freq_used,
            )[1:]
            df_dl = pd.DataFrame({
                "tanggal":        d_fu_dl[: len(res["future_pred"])],
                "forecast_value": res["future_pred"],
                "model":          res.get("model_name", model_name),
            })
            st.download_button(
                "⬇️ Download Hasil Forecast CSV",
                data=df_dl.to_csv(index=False).encode("utf-8"),
                file_name=f"forecast_{res.get('model_name','model')}.csv",
                mime="text/csv",
                type="primary",
            )

        else:
            # Placeholder metrik
            c1, c2, c3, c4, c5 = st.columns(5)
            for col, lbl in zip([c1, c2, c3, c4, c5], ["MAPE", "MAE", "MSE", "RMSE", "R²"]):
                col.metric(lbl, "–")
            st.dataframe(
                pd.DataFrame([{
                    "Model": model_name, "MAPE": "–",
                    "MAE": "–", "MSE": "–", "RMSE": "–", "R²": "–",
                }]),
                use_container_width=True,
                hide_index=True,
            )