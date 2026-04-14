"""
ml_models/ml_forecasting.py
Energy Demand Forecasting pipeline – XGBoost + Scikit-learn.
Supports CSV / XLSX upload. Robust error handling.
"""
from __future__ import annotations

import io
import numpy as np
import pandas as pd
import streamlit as st
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

try:
    from xgboost import XGBRegressor
    _XGB_OK = True
except ImportError:
    from sklearn.ensemble import GradientBoostingRegressor
    _XGB_OK = False

# ── Column detection ──────────────────────────────────────────────────────
_TIME_CANDIDATES = [
    "Tanggal", "Date", "date", "timestamp", "Time_Stamp",
    "datetime", "waktu", "time", "TANGGAL", "DATE",
]
_TARGET_CANDIDATES = [
    "Energy Demand EV (kWh)", "energy_demand_ev", "Energy_Demand",
    "demand_kwh", "kWh", "energy", "Energy", "energi",
    "Energy_Trafo_2", "ENERGY", "kwh",
]


def _find_col(df: pd.DataFrame, candidates: list) -> str | None:
    low = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c in df.columns:
            return c
        if c.lower() in low:
            return low[c.lower()]
    return None


def _engineer(df: pd.DataFrame, time_col: str, target_col: str) -> pd.DataFrame:
    df = df.copy()
    df[time_col] = pd.to_datetime(df[time_col], errors="coerce")
    df = df.dropna(subset=[time_col]).sort_values(time_col).reset_index(drop=True)
    df[target_col] = pd.to_numeric(df[target_col], errors="coerce")
    df = df.dropna(subset=[target_col])

    t = df[time_col]
    df["year"]       = t.dt.year
    df["month"]      = t.dt.month
    df["day"]        = t.dt.day
    df["dayofweek"]  = t.dt.dayofweek
    df["dayofyear"]  = t.dt.dayofyear
    df["weekofyear"] = t.dt.isocalendar().week.astype(int)
    df["quarter"]    = t.dt.quarter
    df["hour"]       = t.dt.hour
    df["is_weekend"] = (t.dt.dayofweek >= 5).astype(int)

    y = df[target_col]
    df["lag_1"]        = y.shift(1)
    df["lag_7"]        = y.shift(7)
    df["lag_30"]       = y.shift(30)
    df["roll_mean_7"]  = y.shift(1).rolling(7,  min_periods=1).mean()
    df["roll_std_7"]   = y.shift(1).rolling(7,  min_periods=1).std().fillna(0)
    df["roll_mean_30"] = y.shift(1).rolling(30, min_periods=1).mean()

    return df.dropna().reset_index(drop=True)


_FEATS = [
    "year", "month", "day", "dayofweek", "dayofyear",
    "weekofyear", "quarter", "hour", "is_weekend",
    "lag_1", "lag_7", "lag_30",
    "roll_mean_7", "roll_std_7", "roll_mean_30",
]


@st.cache_data(show_spinner=False)
def run_forecast(
    file_bytes: bytes,
    file_name: str,
    test_size: float = 0.2,
    n_estimators: int = 300,
    max_depth: int = 6,
    learning_rate: float = 0.05,
) -> dict:
    """
    Full pipeline. Returns dict:
        df_hist, df_pred, metrics, model_name, feature_importance
    """
    # 1. Load file
    buf = io.BytesIO(file_bytes)
    try:
        if file_name.lower().endswith((".xlsx", ".xls")):
            df_raw = pd.read_excel(buf)
        else:
            # try common CSV separators
            df_raw = None
            for sep in [",", ";", "\t"]:
                buf.seek(0)
                try:
                    tmp = pd.read_csv(buf, sep=sep)
                    if tmp.shape[1] > 1:
                        df_raw = tmp
                        break
                except Exception:
                    continue
            if df_raw is None:
                buf.seek(0)
                df_raw = pd.read_csv(buf)
    except Exception as e:
        raise ValueError(f"Gagal membaca file: {e}")

    if df_raw is None or df_raw.empty:
        raise ValueError("File kosong atau tidak dapat dibaca.")

    # 2. Detect columns
    time_col   = _find_col(df_raw, _TIME_CANDIDATES)
    target_col = _find_col(df_raw, _TARGET_CANDIDATES)

    # Fallback: first col as time, first numeric as target
    if time_col is None:
        df_raw.insert(0, "__date__",
                      pd.date_range("2024-01-01", periods=len(df_raw), freq="D"))
        time_col = "__date__"

    if target_col is None:
        nums = df_raw.select_dtypes(include=np.number).columns.tolist()
        if not nums:
            raise ValueError(
                "Tidak ditemukan kolom numerik. "
                "Pastikan file memiliki kolom angka (energi/demand)."
            )
        target_col = nums[0]

    # 3. Feature engineering
    df = _engineer(df_raw[[time_col, target_col]].copy(), time_col, target_col)
    if len(df) < 20:
        raise ValueError(
            f"Data terlalu sedikit ({len(df)} baris valid). Minimal 20 baris."
        )

    # 4. Split
    feats = [f for f in _FEATS if f in df.columns]
    X = df[feats].values
    y = df[target_col].values

    split = int(len(df) * (1 - test_size))
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    # 5. Scale
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s  = scaler.transform(X_test)

    # 6. Train
    if _XGB_OK:
        model = XGBRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            verbosity=0,
            tree_method="hist",
        )
        model.fit(X_train_s, y_train,
                  eval_set=[(X_test_s, y_test)], verbose=False)
        model_name = "XGBoost Regressor"
        feat_imp   = pd.Series(model.feature_importances_, index=feats).sort_values(ascending=False)
    else:
        model = GradientBoostingRegressor(
            n_estimators=min(n_estimators, 200),
            max_depth=max_depth,
            learning_rate=learning_rate,
            random_state=42,
        )
        model.fit(X_train_s, y_train)
        model_name = "GradientBoosting Regressor"
        feat_imp   = pd.Series(model.feature_importances_, index=feats).sort_values(ascending=False)

    # 7. Predict
    y_pred = np.clip(model.predict(X_test_s), 0, None)

    # 8. Metrics
    eps  = 1e-9
    mape = float(np.mean(np.abs((y_test - y_pred) / (np.abs(y_test) + eps))) * 100)
    mae  = float(mean_absolute_error(y_test, y_pred))
    mse  = float(mean_squared_error(y_test, y_pred))
    rmse = float(np.sqrt(mse))
    r2   = float(r2_score(y_test, y_pred))

    # 9. Output DataFrames
    df_hist = df[[time_col, target_col]].copy()
    df_hist.columns = ["Tanggal", "Aktual"]

    df_pred = df.iloc[split:].copy()
    df_pred = df_pred[[time_col, target_col]].copy()
    df_pred.columns = ["Tanggal", "Aktual"]
    df_pred["Prediksi"] = y_pred

    return {
        "df_hist":            df_hist,
        "df_pred":            df_pred,
        "metrics":            {"MAPE": mape, "MAE": mae, "MSE": mse, "RMSE": rmse, "R²": r2},
        "model_name":         model_name,
        "feature_importance": feat_imp,
    }