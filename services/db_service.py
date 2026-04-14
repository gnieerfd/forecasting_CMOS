"""
services/db_service.py
SQLAlchemy ORM + helper functions untuk CMOS MySQL database.
Jika DB tidak tersedia, otomatis fallback ke mock data.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
import streamlit as st
from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# ── DB Config ─────────────────────────────────────────────────────────────
DB_USER     = os.getenv("DB_USER",     "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST     = os.getenv("DB_HOST",     "localhost")
DB_PORT     = os.getenv("DB_PORT",     "3306")
DB_NAME     = os.getenv("DB_NAME",     "cmos_db")

DATABASE_URL = (
    f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)


# ── ORM Base ──────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── ORM Models ───────────────────────────────────────────────────────────

class EnergyLog(Base):
    __tablename__ = "energy_log"
    id             = Column(Integer, primary_key=True, autoincrement=True)
    Time_Stamp     = Column(DateTime, nullable=False, index=True)
    Energy_Trafo_2 = Column(Float, nullable=True)
    station_id     = Column(String(50), nullable=True, index=True)
    connector_id   = Column(Integer, nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow)


class Transaction(Base):
    __tablename__ = "transactions"
    id             = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, nullable=False, unique=True, index=True)
    station_id     = Column(String(50), nullable=True)
    connector_id   = Column(Integer, nullable=True)
    id_tag         = Column(String(100), nullable=True)
    start_time     = Column(DateTime, nullable=True)
    stop_time      = Column(DateTime, nullable=True)
    meter_start    = Column(Float, nullable=True)
    meter_stop     = Column(Float, nullable=True)
    energy_kwh     = Column(Float, nullable=True)
    reason         = Column(String(50), nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow)


class MeterValue(Base):
    __tablename__ = "meter_values"
    id             = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, nullable=False, index=True)
    connector_id   = Column(Integer, nullable=True)
    timestamp      = Column(DateTime, nullable=False, index=True)
    measurand      = Column(String(100), nullable=True)
    value          = Column(Float, nullable=True)
    unit           = Column(String(20), nullable=True)
    context        = Column(String(50), nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow)


# ── Engine ────────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def get_engine():
    try:
        engine = create_engine(
            DATABASE_URL,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            echo=False,
        )
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as exc:
        st.warning(f"⚠️ DB tidak terhubung ({exc}). Menggunakan data demo.")
        return None


def get_session() -> Optional[Session]:
    engine = get_engine()
    if engine is None:
        return None
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return SessionLocal()


def create_tables() -> None:
    engine = get_engine()
    if engine:
        Base.metadata.create_all(bind=engine)


# ── Query Helpers ─────────────────────────────────────────────────────────

@st.cache_data(ttl=30, show_spinner=False)
def fetch_energy_log(station_id: str = "CS_Serpong", limit: int = 500) -> pd.DataFrame:
    """Fetch energy log. Fallback ke mock jika DB tidak tersedia."""
    session = get_session()
    if session:
        try:
            rows = (
                session.query(EnergyLog)
                .filter(EnergyLog.station_id == station_id)
                .order_by(EnergyLog.Time_Stamp.desc())
                .limit(limit)
                .all()
            )
            if rows:
                return pd.DataFrame([
                    {"Time_Stamp": r.Time_Stamp, "Energy_Trafo_2": r.Energy_Trafo_2}
                    for r in rows
                ])
        except Exception:
            pass
        finally:
            session.close()

    return _mock_energy_log()


@st.cache_data(ttl=30, show_spinner=False)
def fetch_transactions(limit: int = 200) -> pd.DataFrame:
    session = get_session()
    if session:
        try:
            rows = (
                session.query(Transaction)
                .order_by(Transaction.transaction_id.desc())
                .limit(limit)
                .all()
            )
            if rows:
                return pd.DataFrame([
                    {
                        "transaction_id": r.transaction_id,
                        "connector_id":   r.connector_id,
                        "start_time":     r.start_time,
                        "energy_kwh":     r.energy_kwh,
                    }
                    for r in rows
                ])
        except Exception:
            pass
        finally:
            session.close()

    return _mock_transactions()


# ── Mock Data Generators ──────────────────────────────────────────────────

def _mock_energy_log() -> pd.DataFrame:
    rng   = np.random.default_rng(7)
    dates = pd.date_range("2025-03-26 08:00", periods=100, freq="3h")
    base  = 188_000.0
    vals  = base + np.cumsum(rng.uniform(5, 80, len(dates)))
    return pd.DataFrame({"Time_Stamp": dates, "Energy_Trafo_2": vals.round(2)})


def _mock_transactions() -> pd.DataFrame:
    rng   = np.random.default_rng(11)
    n     = 15
    t_ids = list(range(379, 379 + n))[::-1]
    dates = pd.date_range("2026-04-08 08:00", periods=n, freq="3h")
    return pd.DataFrame({
        "transaction_id": t_ids,
        "connector_id":   rng.integers(1, 3, n),
        "start_time":     dates,
        "energy_kwh":     rng.uniform(5, 50, n).round(2),
    })