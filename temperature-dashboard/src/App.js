import React, { useState, useEffect, useCallback, useRef } from 'react';
import './App.css';
import DailyStats from './components/DailyStats';
import WeatherDetails from './components/WeatherDetails';
import TemperatureChart from './components/TemperatureChart';
import SyncModal from './components/SyncModal';
import ForecastSection from './components/ForecastSection';
import LocationSelector from './components/LocationSelector';
import { transformApiDailyData, transformApiHourlyData } from './utils/parseCSV';

const API_BASE = 'http://localhost:3002';
const MIN_YEAR = 2026;
const MIN_MONTH = 1;

function App() {
  const now = new Date();
  const maxYear  = now.getFullYear();
  const maxMonth = now.getMonth() + 1;

  // 地區
  const [counties,  setCounties]  = useState([]);
  const [county,    setCounty]    = useState('臺北市');
  const [districts, setDistricts] = useState([]);
  const [district,  setDistrict]  = useState('大安區');

  // 月曆
  const [year,  setYear]  = useState(2026);
  const [month, setMonth] = useState(4);
  const [selectedDay, setSelectedDay] = useState(1);
  const daysInMonth = new Date(year, month, 0).getDate();

  // 資料
  const [dailyData,  setDailyData]  = useState([]);
  const [chartData,  setChartData]  = useState([]);
  const [forecastData, setForecastData] = useState(null);
  const [loading,    setLoading]    = useState(true);
  const [error,      setError]      = useState(null);

  // 縣市歷史資料下載狀態
  const [countySync, setCountySync] = useState({ status: 'idle' });
  const [refreshKey, setRefreshKey] = useState(0);

  // 啟動同步
  const [syncStatus, setSyncStatus] = useState({ status: 'checking', message: '正在檢查最新資料…' });
  const syncTimerRef = useRef(null);

  const canGoPrev = year > MIN_YEAR || month > MIN_MONTH;
  const canGoNext = year < maxYear  || month < maxMonth;

  const prevMonth = () => {
    if (month === 1) { setYear(y => y - 1); setMonth(12); }
    else setMonth(m => m - 1);
    setSelectedDay(1);
  };
  const nextMonth = () => {
    if (month === 12) { setYear(y => y + 1); setMonth(1); }
    else setMonth(m => m + 1);
    setSelectedDay(1);
  };

  // 初始化：載入縣市清單
  useEffect(() => {
    fetch(`${API_BASE}/api/counties`)
      .then(r => r.json())
      .then(({ counties }) => setCounties(counties))
      .catch(() => {});
  }, []);

  // 啟動同步輪詢
  useEffect(() => {
    const poll = async () => {
      try {
        const resp = await fetch(`${API_BASE}/api/sync-status`);
        const data = await resp.json();
        setSyncStatus(data);
        if (data.status === 'done') {
          setYear(data.target_year);
          setMonth(data.target_month);
          setSelectedDay(1);
        } else if (data.status === 'checking' || data.status === 'syncing') {
          syncTimerRef.current = setTimeout(poll, 2000);
        }
      } catch {
        syncTimerRef.current = setTimeout(poll, 2000);
      }
    };
    poll();
    return () => clearTimeout(syncTimerRef.current);
  }, []);

  // 縣市切換：載入行政區清單
  useEffect(() => {
    setDistricts([]);
    fetch(`${API_BASE}/api/districts?county=${encodeURIComponent(county)}`)
      .then(r => r.json())
      .then(({ districts }) => {
        setDistricts(districts);
        setDistrict(prev => districts.includes(prev) ? prev : (districts[0] ?? ''));
      })
      .catch(() => {});
  }, [county]);

  // 縣市切換：檢查歷史資料是否存在，不足則觸發下載
  useEffect(() => {
    let active = true;
    setCountySync({ status: 'idle' });

    const pollSync = async () => {
      if (!active) return;
      try {
        const r = await fetch(`${API_BASE}/api/station-status?county=${encodeURIComponent(county)}`);
        const d = await r.json();
        if (!active) return;
        if (d.sync?.status === 'done') {
          setCountySync({ status: 'done' });
          setRefreshKey(k => k + 1);
        } else if (d.sync?.status === 'error') {
          setCountySync({ status: 'error', message: d.sync.message });
        } else {
          setCountySync({ status: 'syncing', message: d.sync?.message || `正在下載 ${county} 歷史資料…` });
          if (active) setTimeout(pollSync, 3000);
        }
      } catch {
        if (active) setTimeout(pollSync, 3000);
      }
    };

    const checkAndFetch = async () => {
      try {
        const resp = await fetch(`${API_BASE}/api/station-status?county=${encodeURIComponent(county)}`);
        if (!active) return;
        const data = await resp.json();
        if (!active) return;
        if (data.total_records) {
          setCountySync({ status: 'idle' });
        } else {
          setCountySync({ status: 'syncing', message: `正在下載 ${county} 歷史資料…` });
          await fetch(`${API_BASE}/api/fetch-county?county=${encodeURIComponent(county)}`, { method: 'POST' });
          if (!active) return;
          setTimeout(pollSync, 2000);
        }
      } catch {}
    };

    checkAndFetch();
    return () => { active = false; };
  }, [county]);

  // 月份切換：載入日摘要
  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setDailyData([]);
      setChartData([]);
      try {
        const resp = await fetch(
          `${API_BASE}/api/daily?year=${year}&month=${month}&county=${encodeURIComponent(county)}`
        );
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const { data } = await resp.json();
        setDailyData(transformApiDailyData(data, year, month));
        setError(null);
      } catch (e) {
        setError(`載入 ${year}年${month}月 資料失敗：${e.message}`);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [year, month, county, refreshKey]);

  // 選日：載入逐時資料
  useEffect(() => {
    if (!dailyData.length) return;
    const pad = n => String(n).padStart(2, '0');
    fetch(`${API_BASE}/api/hourly?date=${year}-${pad(month)}-${pad(selectedDay)}&county=${encodeURIComponent(county)}`)
      .then(r => r.ok ? r.json() : { data: [] })
      .then(({ data }) => setChartData(transformApiHourlyData(data ?? [])))
      .catch(() => setChartData([]));
  }, [selectedDay, dailyData, year, month, county]);

  // 跨日
  const handleCrossDayRequest = useCallback(async (startDay, endDay) => {
    try {
      const pad = n => String(n).padStart(2, '0');
      const start = `${year}-${pad(month)}-${pad(startDay)}`;
      const end   = `${year}-${pad(month)}-${pad(endDay)}`;
      const resp  = await fetch(
        `${API_BASE}/api/hourly?start_date=${start}&end_date=${end}&county=${encodeURIComponent(county)}`
      );
      if (!resp.ok) return [];
      const { data } = await resp.json();
      return transformApiHourlyData(data ?? [], true);
    } catch { return []; }
  }, [year, month, county]);

  // 預報（只在當月顯示）
  useEffect(() => {
    if (year !== maxYear || month !== maxMonth) {
      setForecastData(null);
      return;
    }
    fetch(`${API_BASE}/api/forecast?county=${encodeURIComponent(county)}&district=${encodeURIComponent(district)}`)
      .then(r => r.ok ? r.json() : null)
      .then(setForecastData)
      .catch(() => setForecastData(null));
  }, [year, month, county, district, maxYear, maxMonth]);

  const showSyncModal = ['checking', 'syncing', 'error'].includes(syncStatus.status);
  const showCountyModal = countySync.status === 'syncing';

  if (loading) return (
    <>
      {showSyncModal && (
        <SyncModal message={syncStatus.message} isError={syncStatus.status === 'error'}
          onClose={() => setSyncStatus({ status: 'idle', message: '' })} />
      )}
      <div className="app loading">載入中...</div>
    </>
  );
  if (error) return <div className="app error">{error}</div>;

  return (
    <div className="app">
      {showSyncModal && (
        <SyncModal message={syncStatus.message} isError={syncStatus.status === 'error'}
          onClose={() => setSyncStatus({ status: 'idle', message: '' })} />
      )}
      {showCountyModal && (
        <SyncModal message={countySync.message} />
      )}

      <header className="app-header">
        <h1>台灣氣溫查詢</h1>
        <p className="subtitle">每日最高最低溫度及逐時氣溫趨勢</p>
        <LocationSelector
          county={county}
          district={district}
          counties={counties}
          districts={districts}
          onCountyChange={c => { setCounty(c); setSelectedDay(1); }}
          onDistrictChange={setDistrict}
        />
        <div className="month-nav">
          <button className="month-btn" onClick={prevMonth} disabled={!canGoPrev}>← 上月</button>
          <span className="month-label">{year}年{month}月</span>
          <button className="month-btn" onClick={nextMonth} disabled={!canGoNext}>下月 →</button>
        </div>
      </header>

      <main className="app-main">
        <DailyStats
          dailyData={dailyData}
          selectedDay={selectedDay}
          onDaySelect={setSelectedDay}
          year={year}
          month={month}
        />

        <ForecastSection data={forecastData} />

        <WeatherDetails dailyData={dailyData} selectedDay={selectedDay} />

        <TemperatureChart
          data={chartData}
          selectedDay={selectedDay}
          dailyData={dailyData}
          onDayChange={setSelectedDay}
          onCrossDayRequest={handleCrossDayRequest}
          daysInMonth={daysInMonth}
          year={year}
          month={month}
        />
      </main>

      <footer className="app-footer">
        <p>資料來源：CODIS 氣候觀測資料查詢服務（中央氣象署）</p>
      </footer>
    </div>
  );
}

export default App;
