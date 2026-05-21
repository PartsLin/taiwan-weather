import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path

DB_PATH = (
    Path(sys.executable).parent / "weather.db"
    if getattr(sys, "frozen", False)
    else Path(__file__).parent / "weather.db"
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS forecasts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    location      TEXT    NOT NULL,
    issued_at     TEXT    NOT NULL,  -- 預報發布時間 (整點, YYYY-MM-DD HH:00:00)
    forecast_time TEXT    NOT NULL,  -- 預報目標時間 YYYY-MM-DD HH:MM:SS
    temperature   REAL,             -- 預報氣溫 °C
    wx            TEXT,             -- 天氣現象描述
    pop6h         REAL,             -- 6小時降雨機率 %
    fetched_at    TEXT    DEFAULT (datetime('now', 'localtime')),
    UNIQUE(location, issued_at, forecast_time)
);

CREATE INDEX IF NOT EXISTS idx_forecast_issued
    ON forecasts(location, issued_at);

CREATE TABLE IF NOT EXISTS observations (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    station_id             TEXT    NOT NULL,
    obs_date               TEXT    NOT NULL,  -- YYYY-MM-DD
    obs_hour               INTEGER NOT NULL,  -- 1~24
    temperature            REAL,              -- 氣溫 °C
    cloud_amount           REAL,              -- 衛星總雲量 0~10
    sunshine_duration      REAL,              -- 日照時數 (時/時，0~1)
    precipitation_duration REAL,              -- 降水時數 (時/時，0~1)
    relative_humidity      REAL,              -- 相對濕度 %
    uv_index               REAL,              -- 紫外線指數
    fetched_at             TEXT    DEFAULT (datetime('now', 'localtime')),
    UNIQUE(station_id, obs_date, obs_hour)
);

CREATE INDEX IF NOT EXISTS idx_obs_date
    ON observations(station_id, obs_date);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(_SCHEMA)


def upsert_observations(rows: list[dict]):
    sql = """
        INSERT INTO observations
            (station_id, obs_date, obs_hour,
             temperature, cloud_amount, sunshine_duration,
             precipitation_duration, relative_humidity, uv_index)
        VALUES
            (:station_id, :obs_date, :obs_hour,
             :temperature, :cloud_amount, :sunshine_duration,
             :precipitation_duration, :relative_humidity, :uv_index)
        ON CONFLICT(station_id, obs_date, obs_hour) DO UPDATE SET
            temperature            = COALESCE(excluded.temperature,            temperature),
            cloud_amount           = COALESCE(excluded.cloud_amount,           cloud_amount),
            sunshine_duration      = COALESCE(excluded.sunshine_duration,      sunshine_duration),
            precipitation_duration = COALESCE(excluded.precipitation_duration, precipitation_duration),
            relative_humidity      = COALESCE(excluded.relative_humidity,      relative_humidity),
            uv_index               = COALESCE(excluded.uv_index,               uv_index),
            fetched_at             = datetime('now', 'localtime')
    """
    with get_conn() as conn:
        conn.executemany(sql, rows)


def get_daily_summary(station_id: str, year: int, month: int) -> list[dict]:
    sql = """
        SELECT
            obs_date,
            MAX(temperature)            AS max_temp,
            MIN(temperature)            AS min_temp,
            ROUND(AVG(temperature), 1)  AS avg_temp,
            ROUND(AVG(cloud_amount), 1) AS avg_cloud,
            ROUND(SUM(sunshine_duration),      1) AS total_sunshine,
            ROUND(SUM(precipitation_duration), 1) AS total_precipitation,
            ROUND(AVG(relative_humidity), 1)  AS avg_humidity
        FROM observations
        WHERE station_id = ?
          AND obs_date LIKE ?
        GROUP BY obs_date
        ORDER BY obs_date
    """
    prefix = f"{year}-{month:02d}-%"
    with get_conn() as conn:
        rows = conn.execute(sql, (station_id, prefix)).fetchall()
    return [dict(r) for r in rows]


def get_hourly_data(
    station_id: str,
    obs_date: str = None,
    start_date: str = None,
    end_date: str = None,
) -> list[dict]:
    """
    單日：get_hourly_data(sid, obs_date="2026-04-01")
    區間：get_hourly_data(sid, start_date="2026-04-01", end_date="2026-04-07")
    """
    if obs_date:
        sql = """
            SELECT obs_date, obs_hour,
                   temperature, cloud_amount, sunshine_duration,
                   precipitation_duration, relative_humidity, uv_index
            FROM observations
            WHERE station_id = ? AND obs_date = ?
            ORDER BY obs_hour
        """
        params = (station_id, obs_date)
    else:
        sql = """
            SELECT obs_date, obs_hour,
                   temperature, cloud_amount, sunshine_duration,
                   precipitation_duration, relative_humidity, uv_index
            FROM observations
            WHERE station_id = ?
              AND obs_date BETWEEN ? AND ?
            ORDER BY obs_date, obs_hour
        """
        params = (station_id, start_date, end_date)

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def upsert_forecasts(rows: list[dict]):
    sql = """
        INSERT INTO forecasts (location, issued_at, forecast_time, temperature, wx, pop6h)
        VALUES (:location, :issued_at, :forecast_time, :temperature, :wx, :pop6h)
        ON CONFLICT(location, issued_at, forecast_time) DO UPDATE SET
            temperature = COALESCE(excluded.temperature, temperature),
            wx          = COALESCE(excluded.wx,          wx),
            pop6h       = COALESCE(excluded.pop6h,       pop6h),
            fetched_at  = datetime('now', 'localtime')
    """
    with get_conn() as conn:
        conn.executemany(sql, rows)


def get_db_status() -> dict:
    sql = """
        SELECT
            COUNT(*)         AS total_records,
            MIN(obs_date)    AS earliest_date,
            MAX(obs_date)    AS latest_date,
            MAX(fetched_at)  AS last_fetched,
            COUNT(DISTINCT station_id) AS station_count
        FROM observations
    """
    with get_conn() as conn:
        row = conn.execute(sql).fetchone()
    return dict(row) if row else {}


def get_station_status(station_id: str) -> dict:
    sql = """
        SELECT
            COUNT(*)      AS total_records,
            MIN(obs_date) AS earliest_date,
            MAX(obs_date) AS latest_date,
            MAX(fetched_at) AS last_fetched
        FROM observations
        WHERE station_id = ?
    """
    with get_conn() as conn:
        row = conn.execute(sql, (station_id,)).fetchone()
    return dict(row) if row else {}
