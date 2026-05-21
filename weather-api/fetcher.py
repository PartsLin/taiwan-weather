"""
資料來源：CODIS 氣候觀測資料查詢服務
端點：POST https://codis.cwa.gov.tw/api/station
無需 API Key
"""

import asyncio
import calendar
import re
from datetime import datetime, timedelta
from pathlib import Path

import httpx

from db import upsert_observations

CODIS_URL = "https://codis.cwa.gov.tw/api/station"

# CODIS item 設定：form item 名稱 → (DB 欄位, 回應 JSON key, 值子欄位)
# 實測回應：AirTemperature→{"Instantaneous":v}, SunshineDuration→{"Total":v},
#           TotalCloudAmountSat 回應 key 為 TotalCloudAmount→{"SatRetrieved":v}
ITEMS = {
    "AirTemperature":        ("temperature",             "AirTemperature",       "Instantaneous"),
    "TotalCloudAmountSat":   ("cloud_amount",            "TotalCloudAmount",     "SatRetrieved"),
    "SunshineDuration":      ("sunshine_duration",       "SunshineDuration",     "Total"),
    "PrecipitationDuration": ("precipitation_duration",  "PrecipitationDuration","Total"),
    "RelativeHumidity":      ("relative_humidity",       "RelativeHumidity",     "Instantaneous"),
    "UVIndex":               ("uv_index",                "UVIndex",              "Instantaneous"),
}


def _parse_data_time(dt_str: str):
    """
    將 DataTime 字串轉換為 (obs_date, obs_hour)。
    CODIS 使用 T01:00:00~T23:00:00 代表當日第 1~23 小時，
    T00:00:00 代表前一日第 24 小時（午夜）。
    """
    obs_date = dt_str[:10]
    hour_int = int(dt_str[11:13])
    if hour_int == 0:
        d = datetime.strptime(obs_date, "%Y-%m-%d") - timedelta(days=1)
        return d.strftime("%Y-%m-%d"), 24
    return obs_date, hour_int


async def _fetch_item(
    client: httpx.AsyncClient,
    station_id: str,
    year: int,
    month: int,
    item: str,
    stn_type: str = "cwb",
) -> list[dict]:
    last_day = calendar.monthrange(year, month)[1]
    data = {
        "stn_ID":   station_id,
        "stn_type": stn_type,
        "date":     f"{year}-{month:02d}-01T00:00:00+08:00",
        "type":     "one_date",
        "more":     "",
        "start":    f"{year}-{month:02d}-01T00:00:00",
        "end":      f"{year}-{month:02d}-{last_day:02d}T23:59:59",
        "item":     item,
    }
    resp = await client.post(CODIS_URL, data=data, timeout=30)
    resp.raise_for_status()
    result = resp.json()

    hour_block = result.get("hour", {})
    if hour_block.get("code") != 200:
        raise RuntimeError(f"CODIS API 錯誤：{hour_block.get('message')}")

    station_data = hour_block.get("data", [])
    if not station_data:
        return []

    field, resp_key, val_key = ITEMS[item]
    rows = []
    for entry in station_data[0].get("dts", []):
        raw_obj = entry.get(resp_key)
        if raw_obj is None:
            value = None
        elif isinstance(raw_obj, dict):
            raw = raw_obj.get(val_key)
            try:
                value = float(raw) if raw is not None else None
            except (TypeError, ValueError):
                value = None
        else:
            try:
                value = float(raw_obj)
            except (TypeError, ValueError):
                value = None

        obs_date, obs_hour = _parse_data_time(entry["DataTime"])
        rows.append({
            "obs_date": obs_date,
            "obs_hour": obs_hour,
            field:      value,
        })
    return rows


async def fetch_month(
    station_id: str = "466920",
    year: int = None,
    month: int = None,
    items: list[str] = None,
    stn_type: str = "cwb",
) -> dict:
    """
    非同步抓取指定月份所有項目並寫入 SQLite。
    回傳 {"fetched": N, "year": y, "month": m}
    """
    now = datetime.now()
    y = year or now.year
    m = month or now.month
    target_items = items or list(ITEMS.keys())

    # 以日期+小時為 key 合併各項目資料
    merged: dict[tuple, dict] = {}

    async with httpx.AsyncClient() as client:
        tasks = [_fetch_item(client, station_id, y, m, item, stn_type) for item in target_items]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for item, result in zip(target_items, results):
        if isinstance(result, Exception):
            print(f"[fetcher] {item} 抓取失敗：{result}")
            continue
        field = ITEMS[item][0]
        for row in result:
            key = (row["obs_date"], row["obs_hour"])
            if key not in merged:
                merged[key] = {
                    "station_id":             station_id,
                    "obs_date":               row["obs_date"],
                    "obs_hour":               row["obs_hour"],
                    "temperature":            None,
                    "cloud_amount":           None,
                    "sunshine_duration":      None,
                    "precipitation_duration": None,
                    "relative_humidity":      None,
                    "uv_index":               None,
                }
            merged[key][field] = row[field]

    all_rows = list(merged.values())
    if all_rows:
        upsert_observations(all_rows)

    return {"fetched": len(all_rows), "year": y, "month": m, "station": station_id}


def import_csv_dir(csv_dir: str, station_id: str = "466920") -> dict:
    """
    將既有的 CSV 檔（rows=日, cols=小時）批次匯入 SQLite。
    支援 public/ 資料夾下的月份 CSV。
    """
    dir_path = Path(csv_dir)
    pattern = re.compile(
        rf"{re.escape(station_id)}-(\d{{4}})-(\d{{2}})-(\w+)-hour\.csv"
    )

    # 先依 (year, month, day, hour) 合併各項目
    merged: dict[tuple, dict] = {}

    for csv_file in sorted(dir_path.glob(f"{station_id}-*-hour.csv")):
        m = pattern.match(csv_file.name)
        if not m:
            continue
        year, month, item = m.group(1), m.group(2), m.group(3)
        if item not in ITEMS:
            continue
        field = ITEMS[item][0]

        lines = csv_file.read_text(encoding="utf-8").strip().splitlines()
        # 第 0 列 header，最後一列月平均 → 跳過
        for line in lines[1:-1]:
            parts = [v.strip('"') for v in line.split(",")]
            day_str = parts[0].zfill(2)
            hourly = parts[1:-1]   # 24 欄，去掉最後的月均
            for idx, val in enumerate(hourly):
                obs_hour = idx + 1
                obs_date = f"{year}-{month}-{day_str}"
                key = (obs_date, obs_hour)
                if key not in merged:
                    merged[key] = {
                        "station_id":             station_id,
                        "obs_date":               obs_date,
                        "obs_hour":               obs_hour,
                        "temperature":            None,
                        "cloud_amount":           None,
                        "sunshine_duration":      None,
                        "precipitation_duration": None,
                        "relative_humidity":      None,
                        "uv_index":               None,
                    }
                if val not in ("--", ""):
                    try:
                        merged[key][field] = float(val)
                    except ValueError:
                        pass

    all_rows = list(merged.values())
    if all_rows:
        upsert_observations(all_rows)
    return {"imported": len(all_rows), "source": str(dir_path)}
