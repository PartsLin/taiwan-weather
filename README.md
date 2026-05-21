# 台灣氣溫查詢

全台 22 縣市歷史氣象資料查詢與天氣預報儀表板。

![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite)

## 功能

- **月曆檢視** — 每日最高／最低／平均氣溫，天氣圖示
- **逐時折線圖** — 溫度、日照時數、降水時數，單日或跨日檢視
- **缺值處理** — 測站缺報時自動插值連線，hover 顯示「缺資料」
- **天氣預報** — 整合 CWA 開放資料，顯示未來 7 天逐時預報
- **全台縣市** — 支援 22 縣市切換，首次選取自動下載歷史資料
- **系統匣常駐** — 背景服務，選單提供重啟、更新資料、關閉等操作

## 資料來源

| 資料 | 來源 |
|------|------|
| 歷史逐時觀測 | [CODIS 氣候觀測資料查詢服務（中央氣象署）](https://codis.cwa.gov.tw) |
| 天氣預報 | [CWA 開放資料平台](https://opendata.cwa.gov.tw) |

## 系統需求

| 項目 | 版本 |
|------|------|
| Python | 3.10 以上 |
| Node.js | 18 以上（僅首次建置前端需要） |

> 使用 `taiwan-weather.exe` 啟動時，會自動偵測並安裝缺少的環境。

---

## 快速開始

### 方法一：使用啟動器（推薦）

1. 建置啟動器（需要 Python + PyInstaller）：
   ```
   build_launcher.bat
   ```
2. 點兩下 `taiwan-weather.exe`
   - 首次執行：自動安裝缺少的套件並建置前端，完成後進入系統匣
   - 之後執行：直接啟動，不顯示視窗

### 方法二：手動啟動（開發用）

```bash
# 安裝 Python 套件
pip install -r weather-api/requirements.txt

# 建置前端（首次）
cd temperature-dashboard
npm install
npm run build
cd ..

# 啟動服務
cd weather-api
python tray.py
```

瀏覽器開啟 [http://localhost:3002](http://localhost:3002)

---

## 專案結構

```
taiwan-weather/
├── weather-api/
│   ├── app.py          # FastAPI 主程式（API + 靜態前端服務）
│   ├── db.py           # SQLite 資料存取
│   ├── fetcher.py      # CODIS API 資料抓取
│   ├── tray.py         # 系統匣服務入口
│   └── requirements.txt
├── temperature-dashboard/
│   ├── src/
│   │   ├── App.js
│   │   ├── components/
│   │   └── utils/
│   └── package.json
├── launcher/
│   ├── main.py         # 啟動器（環境檢查 + 安裝）
│   └── weather.spec    # PyInstaller 設定
├── build_launcher.bat  # 一鍵建置啟動器
└── start.bat           # 開發用快速啟動
```

---

## API 端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/api/counties` | 支援縣市清單 |
| GET | `/api/districts?county=X` | 縣市下的行政區 |
| GET | `/api/daily?year=&month=&county=` | 月曆每日摘要 |
| GET | `/api/hourly?date=&county=` | 逐時資料 |
| GET | `/api/forecast?county=&district=` | 天氣預報 |
| GET | `/api/station-status?county=` | 縣市資料狀態 |
| POST | `/api/fetch-county?county=` | 觸發縣市歷史資料下載 |
| POST | `/api/update-all` | 更新所有已下載縣市至本月 |
| POST | `/api/refresh-forecast` | 清除預報快取 |
| GET | `/api/sync-status` | 啟動同步進度 |

---

## 系統匣選單

右鍵點選工作列圖示：

- **開啟介面** — 在瀏覽器開啟儀表板
- **重啟服務** — 重新啟動後端服務
- **更新歷史資料** — 補抓所有已下載縣市至本月最新資料
- **更新預報資料** — 清除快取，下次開啟頁面自動重新抓取
- **關閉** — 停止服務並退出

---

## 建置啟動器

需要先安裝 PyInstaller：

```bash
pip install pyinstaller
```

執行建置：

```bash
build_launcher.bat
```

輸出：`taiwan-weather.exe`（約 15–20 MB）

**發佈時需包含：**
```
taiwan-weather.exe
weather-api/
temperature-dashboard/
```

收到 `taiwan-weather.exe` 的使用者直接點兩下即可，啟動器會自動處理所有環境安裝。

---

## 技術架構

```
瀏覽器
  └── http://localhost:3002
        └── FastAPI（uvicorn）
              ├── /api/*        歷史資料、預報、狀態
              └── /*            React SPA（build/）
                    └── SQLite（weather.db）
                          ├── observations  逐時觀測紀錄
                          └── forecasts     預報紀錄（含發布時間）
```

- **歷史資料**：CODIS API → SQLite UPSERT，依需求按縣市下載
- **預報資料**：CWA OpenData → 快取 1 小時，同時寫入 DB 供未來準確率分析
- **系統匣**：pystray + uvicorn 背景執行緒，啟動器透過系統 Python 啟動
