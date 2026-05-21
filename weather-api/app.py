"""
全台氣象資料 API — port 3002
啟動：python app.py
"""

import asyncio
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx
import uvicorn

from db import (
    get_daily_summary, get_db_status, get_hourly_data,
    get_station_status, init_db, upsert_forecasts,
)
from fetcher import fetch_month, import_csv_dir

CWA_API_KEY  = "CWA-F306EB1C-CC27-4C81-9333-71228FF89F28"
CWA_BASE_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore"

# ── 縣市對照表 ──────────────────────────────────────────────

# CWA 預報資料集（縣市 → dataset ID + 資料間隔小時數）
COUNTY_FORECAST: dict[str, dict] = {
    "臺北市": {"dataset": "F-D0047-061", "interval": 1},
    "高雄市": {"dataset": "F-D0047-065", "interval": 1},
    "新北市": {"dataset": "F-D0047-069", "interval": 1},
    "臺中市": {"dataset": "F-D0047-073", "interval": 1},
    "臺南市": {"dataset": "F-D0047-077", "interval": 1},
    "連江縣": {"dataset": "F-D0047-081", "interval": 1},
    "金門縣": {"dataset": "F-D0047-085", "interval": 1},
    "宜蘭縣": {"dataset": "F-D0047-001", "interval": 3},
    "桃園市": {"dataset": "F-D0047-005", "interval": 3},
    "新竹縣": {"dataset": "F-D0047-009", "interval": 3},
    "苗栗縣": {"dataset": "F-D0047-013", "interval": 3},
    "彰化縣": {"dataset": "F-D0047-017", "interval": 3},
    "南投縣": {"dataset": "F-D0047-021", "interval": 3},
    "雲林縣": {"dataset": "F-D0047-025", "interval": 3},
    "嘉義縣": {"dataset": "F-D0047-029", "interval": 3},
    "屏東縣": {"dataset": "F-D0047-033", "interval": 3},
    "臺東縣": {"dataset": "F-D0047-037", "interval": 3},
    "花蓮縣": {"dataset": "F-D0047-041", "interval": 3},
    "澎湖縣": {"dataset": "F-D0047-045", "interval": 3},
    "基隆市": {"dataset": "F-D0047-049", "interval": 3},
    "新竹市": {"dataset": "F-D0047-053", "interval": 3},
    "嘉義市": {"dataset": "F-D0047-057", "interval": 3},
}

# CODIS 歷史資料代表測站
COUNTY_STATIONS: dict[str, dict] = {
    "臺北市": {"station_id": "466920", "stn_type": "cwb"},
    "新北市": {"station_id": "466881", "stn_type": "cwb"},
    "基隆市": {"station_id": "466940", "stn_type": "cwb"},
    "宜蘭縣": {"station_id": "467080", "stn_type": "cwb"},
    "桃園市": {"station_id": "467050", "stn_type": "cwb"},
    "新竹市": {"station_id": "C0D660", "stn_type": "auto_C0"},
    "新竹縣": {"station_id": "467571", "stn_type": "cwb"},
    "苗栗縣": {"station_id": "467280", "stn_type": "cwb"},
    "臺中市": {"station_id": "467490", "stn_type": "cwb"},
    "彰化縣": {"station_id": "467270", "stn_type": "cwb"},
    "南投縣": {"station_id": "467650", "stn_type": "cwb"},
    "雲林縣": {"station_id": "467290", "stn_type": "cwb"},
    "嘉義市": {"station_id": "467480", "stn_type": "cwb"},
    "嘉義縣": {"station_id": "467530", "stn_type": "cwb"},
    "臺南市": {"station_id": "467410", "stn_type": "cwb"},
    "高雄市": {"station_id": "467441", "stn_type": "cwb"},
    "屏東縣": {"station_id": "467590", "stn_type": "cwb"},
    "臺東縣": {"station_id": "467660", "stn_type": "cwb"},
    "花蓮縣": {"station_id": "466990", "stn_type": "cwb"},
    "澎湖縣": {"station_id": "467350", "stn_type": "cwb"},
    "金門縣": {"station_id": "467110", "stn_type": "cwb"},
    "連江縣": {"station_id": "467990", "stn_type": "cwb"},
}

COUNTIES = list(COUNTY_FORECAST.keys())

_forecast_cache:  dict = {}  # f"{county}/{district}" → {"data": ..., "cached_at": datetime}
_districts_cache: dict = {}  # county → list[str]
_county_sync:     dict = {}  # station_id → {"status": ..., "message": ...}

# React build 目錄（dev 時在 ../temperature-dashboard/build/）
_BUILD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "..", "temperature-dashboard", "build")

scheduler = AsyncIOScheduler(timezone="Asia/Taipei")

_sync: dict = {
    "status": "checking",
    "message": "正在檢查最新資料…",
    "target_year": None,
    "target_month": None,
}


# ── 內部工具 ────────────────────────────────────────────────

def _get_station(county: str) -> tuple[str, str]:
    """回傳 (station_id, stn_type)。"""
    info = COUNTY_STATIONS.get(county)
    if not info:
        raise HTTPException(status_code=400, detail=f"不支援的縣市：{county}")
    return info["station_id"], info["stn_type"]


async def _fetch_districts(county: str) -> list[str]:
    if county in _districts_cache:
        return _districts_cache[county]
    cfg = COUNTY_FORECAST.get(county)
    if not cfg:
        return []
    url = f"{CWA_BASE_URL}/{cfg['dataset']}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params={"Authorization": CWA_API_KEY}, timeout=15)
    if not resp.is_success:
        return []
    locs = resp.json()["records"]["Locations"][0]["Location"]
    districts = [l["LocationName"] for l in locs]
    _districts_cache[county] = districts
    return districts


async def _startup_sync(county: str = "臺北市"):
    global _sync
    now = datetime.now()
    station_id, stn_type = _get_station(county)

    status = get_station_status(station_id)
    latest = status.get("latest_date")
    since_y, since_m = (int(latest[:4]), int(latest[5:7])) if latest else (2026, 1)

    months: list[tuple[int, int]] = []
    y, m = since_y, since_m
    while (y, m) <= (now.year, now.month):
        months.append((y, m))
        m += 1
        if m > 12:
            m, y = 1, y + 1

    _sync = {"status": "syncing", "message": f"正在下載 {since_y}/{since_m:02d} 資料…",
             "target_year": now.year, "target_month": now.month}
    try:
        for y, m in months:
            _sync["message"] = f"正在下載 {y}/{m:02d} 資料…"
            result = await fetch_month(station_id=station_id, year=y, month=m, stn_type=stn_type)
            print(f"[startup-sync] {y}/{m:02d} → {result['fetched']} 筆")
        _sync = {"status": "done", "message": "資料已更新至最新！",
                 "target_year": now.year, "target_month": now.month}
    except Exception as e:
        _sync = {"status": "error", "message": f"更新失敗：{e}",
                 "target_year": None, "target_month": None}


async def _update_all_counties():
    """更新所有已有資料的縣市至本月。"""
    now = datetime.now()
    for county, info in COUNTY_STATIONS.items():
        station_id = info["station_id"]
        stn_type   = info["stn_type"]
        status = get_station_status(station_id)
        if not status.get("total_records"):
            continue
        latest = status.get("latest_date")
        since_y = int(latest[:4]) if latest else now.year
        since_m = int(latest[5:7]) if latest else now.month
        y, m = since_y, since_m
        while (y, m) <= (now.year, now.month):
            try:
                result = await fetch_month(station_id=station_id, year=y, month=m,
                                           stn_type=stn_type)
                print(f"[update-all] {county} {y}/{m:02d} → {result['fetched']} 筆")
            except Exception as e:
                print(f"[update-all] {county} {y}/{m:02d} 失敗: {e}")
            m += 1
            if m > 12:
                m, y = 1, y + 1


async def _fetch_county_all(county: str):
    """背景補抓指定縣市從 2026/1 至今的所有資料。"""
    station_id, stn_type = _get_station(county)
    _county_sync[station_id] = {"status": "syncing", "message": f"正在下載 {county} 資料…"}
    now = datetime.now()

    status = get_station_status(station_id)
    latest = status.get("latest_date")
    since_y, since_m = (int(latest[:4]), int(latest[5:7])) if latest else (2026, 1)

    try:
        y, m = since_y, since_m
        while (y, m) <= (now.year, now.month):
            _county_sync[station_id]["message"] = f"正在下載 {county} {y}/{m:02d}…"
            result = await fetch_month(station_id=station_id, year=y, month=m, stn_type=stn_type)
            print(f"[county-sync] {county} {y}/{m:02d} → {result['fetched']} 筆")
            m += 1
            if m > 12:
                m, y = 1, y + 1
        _county_sync[station_id] = {"status": "done", "message": f"{county} 資料已更新"}
    except Exception as e:
        _county_sync[station_id] = {"status": "error", "message": str(e)}


# ── FastAPI 應用 ────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    asyncio.create_task(_startup_sync("臺北市"))
    scheduler.add_job(
        fetch_month, "cron", hour=6, minute=0,
        kwargs={"station_id": "466920", "stn_type": "cwb"},
    )
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="全台氣象資料 API", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── 地區端點 ────────────────────────────────────────────────

@app.get("/api/counties", summary="支援的縣市清單")
async def list_counties():
    return {"counties": COUNTIES}


@app.get("/api/districts", summary="縣市下的鄉鎮市區")
async def list_districts(county: str = Query(default="臺北市")):
    districts = await _fetch_districts(county)
    return {"county": county, "districts": districts}


# ── 歷史資料端點 ────────────────────────────────────────────

@app.get("/api/daily", summary="每日摘要（月曆用）")
async def daily_summary(
    year:    int = Query(default=2026),
    month:   int = Query(default=4),
    county:  str = Query(default="臺北市"),
    station: str = Query(default=None),
):
    sid = station or _get_station(county)[0]
    data = get_daily_summary(sid, year, month)
    return {"station": sid, "county": county, "year": year, "month": month, "data": data}


@app.get("/api/hourly", summary="逐時資料（折線圖用）")
async def hourly_data(
    date:       str = Query(default=None),
    start_date: str = Query(default=None),
    end_date:   str = Query(default=None),
    county:     str = Query(default="臺北市"),
    station:    str = Query(default=None),
):
    if not date and not (start_date and end_date):
        raise HTTPException(status_code=400, detail="請提供 date 或 start_date + end_date")
    sid = station or _get_station(county)[0]
    data = get_hourly_data(sid, obs_date=date, start_date=start_date, end_date=end_date)
    if not data:
        raise HTTPException(status_code=404, detail="查無資料")
    return {"station": sid, "data": data}


@app.get("/api/station-status", summary="縣市歷史資料狀態")
async def county_data_status(county: str = Query(default="臺北市")):
    station_id, _ = _get_station(county)
    status = get_station_status(station_id)
    sync = _county_sync.get(station_id, {"status": "idle"})
    return {"county": county, "station_id": station_id, **status, "sync": sync}


# ── 資料抓取端點 ────────────────────────────────────────────

@app.post("/api/fetch", summary="手動觸發抓取（單月）")
async def manual_fetch(
    background_tasks: BackgroundTasks,
    year:    int = Query(default=None),
    month:   int = Query(default=None),
    county:  str = Query(default="臺北市"),
):
    now = datetime.now()
    y = year  or now.year
    m = month or now.month
    station_id, stn_type = _get_station(county)
    background_tasks.add_task(fetch_month, station_id=station_id, year=y, month=m, stn_type=stn_type)
    return {"message": f"已排程抓取 {county} {y}/{m:02d}", "status": "queued"}


@app.post("/api/fetch-county", summary="補抓縣市所有歷史資料")
async def fetch_county(
    background_tasks: BackgroundTasks,
    county: str = Query(default="臺北市"),
):
    station_id, _ = _get_station(county)
    sync = _county_sync.get(station_id, {})
    if sync.get("status") == "syncing":
        return {"message": f"{county} 正在下載中", "status": "already_running"}
    background_tasks.add_task(_fetch_county_all, county)
    return {"message": f"已排程下載 {county} 歷史資料", "status": "queued"}


@app.post("/api/fetch-all", summary="從指定月份抓到本月（初始化用）")
async def fetch_all(
    background_tasks: BackgroundTasks,
    since_year:  int = Query(default=2026),
    since_month: int = Query(default=1),
    county:      str = Query(default="臺北市"),
):
    station_id, stn_type = _get_station(county)

    async def _run():
        now = datetime.now()
        y, m = since_year, since_month
        while (y, m) <= (now.year, now.month):
            await fetch_month(station_id=station_id, year=y, month=m, stn_type=stn_type)
            m += 1
            if m > 12:
                m, y = 1, y + 1

    background_tasks.add_task(_run)
    return {"message": f"已排程從 {since_year}/{since_month:02d} 抓 {county} 至本月", "status": "queued"}


# ── 預報端點 ────────────────────────────────────────────────

def _safe_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _parse_forecast(raw: dict, county: str, target_location: str) -> dict:
    locs = raw["records"]["Locations"][0]["Location"]
    loc  = next((l for l in locs if l["LocationName"] == target_location), locs[0])
    elem_map = {el["ElementName"]: el["Time"] for el in loc["WeatherElement"]}

    def to_dt(iso: str) -> str:
        return iso[:10] + " " + iso[11:19]

    def slot_key(s: dict) -> str:
        return to_dt(s.get("DataTime") or s.get("StartTime", ""))

    wx_elem  = next((v for k, v in elem_map.items() if k == "天氣現象"), [])
    pop_elem = next((v for k, v in elem_map.items() if "降雨機率" in k), [])
    tmp_elem = next((v for k, v in elem_map.items() if k == "溫度"), [])

    wx_map  = {slot_key(s): s["ElementValue"][0].get("Weather") for s in wx_elem}
    pop_map = {slot_key(s): _safe_float(s["ElementValue"][0].get("ProbabilityOfPrecipitation"))
               for s in pop_elem}

    hourly = []
    for slot in tmp_elem:
        dt      = slot_key(slot)
        pop_key = max((k for k in pop_map if k <= dt), default=None)
        wx_key  = max((k for k in wx_map  if k <= dt), default=None)
        hourly.append({
            "dataTime":    dt,
            "temperature": _safe_float(slot["ElementValue"][0].get("Temperature")),
            "wx":          wx_map.get(wx_key),
            "pop6h":       pop_map.get(pop_key),
        })

    return {"county": county, "location": loc["LocationName"], "hourly": hourly}


@app.get("/api/forecast", summary="天氣預報")
async def get_forecast(
    county:   str = Query(default="臺北市"),
    district: str = Query(default="大安區"),
):
    cache_key = f"{county}/{district}"
    now = datetime.now()
    cached = _forecast_cache.get(cache_key)
    if cached and (now - cached["cached_at"]).total_seconds() < 3600:
        return cached["data"]

    cfg = COUNTY_FORECAST.get(county)
    if not cfg:
        raise HTTPException(status_code=400, detail=f"不支援的縣市：{county}")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{CWA_BASE_URL}/{cfg['dataset']}",
            params={"Authorization": CWA_API_KEY, "locationName": district,
                    "elementName": "T,PoP6h,Wx"},
            timeout=15,
        )
    resp.raise_for_status()
    result = _parse_forecast(resp.json(), county, district)

    issued_at = now.replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:00:00")
    db_rows = [
        {"location": result["location"], "issued_at": issued_at,
         "forecast_time": h["dataTime"], "temperature": h["temperature"],
         "wx": h["wx"], "pop6h": h["pop6h"]}
        for h in result["hourly"]
    ]
    if db_rows:
        upsert_forecasts(db_rows)

    _forecast_cache[cache_key] = {"data": result, "cached_at": now}
    return result


# ── 狀態端點 ────────────────────────────────────────────────

@app.get("/api/status", summary="資料庫狀態")
async def status():
    return get_db_status()


@app.get("/api/sync-status", summary="啟動同步進度")
async def get_sync_status():
    return _sync


@app.post("/api/update-all", summary="更新所有已有資料的縣市至本月")
async def update_all(background_tasks: BackgroundTasks):
    background_tasks.add_task(_update_all_counties)
    return {"message": "已排程更新所有縣市", "status": "queued"}


@app.post("/api/refresh-forecast", summary="清除預報快取（下次開頁面自動重抓）")
async def refresh_forecast_cache():
    _forecast_cache.clear()
    return {"message": "預報快取已清除", "status": "ok"}


# ── 前端靜態服務 ────────────────────────────────────────────
if os.path.isdir(_BUILD_DIR):
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=_BUILD_DIR, html=True), name="frontend")


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=3002, reload=True)
