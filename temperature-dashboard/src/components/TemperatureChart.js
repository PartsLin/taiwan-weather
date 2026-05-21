import React, { useState, useEffect, useRef } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import './TemperatureChart.css';

const METRIC_CONFIG = {
  temperature:   { label: '溫度',  dataKey: 'temperature',  color: '#ff6b6b', yAxisLabel: '溫度 (°C)',    domain: ['dataMin - 2', 'dataMax + 2'], formatter: v => `${v.toFixed(1)}°C`   },
  sunshine:      { label: '日照',  dataKey: 'sunshine',     color: '#f59f00', yAxisLabel: '日照時數 (時)', domain: [0, 1],                         formatter: v => `${v.toFixed(2)} 時`  },
  precipitation: { label: '降水',  dataKey: 'precipitation',color: '#4a9eff', yAxisLabel: '降水時數 (時)', domain: [0, 1],                         formatter: v => `${v.toFixed(2)} 時`  },
};

const CustomTooltip = ({ active, payload, label, metric }) => {
  if (!active || !payload || !payload.length) return null;
  const isMissing = !!payload[0]?.payload?._missing;
  return (
    <div style={{ background: 'rgba(255,255,255,0.95)', border: '1px solid #ddd', borderRadius: 6, padding: '6px 12px', fontSize: 13 }}>
      <p style={{ margin: '0 0 4px', color: '#555' }}>時間：{label}</p>
      {isMissing
        ? <p style={{ margin: 0, color: '#aaa', fontStyle: 'italic' }}>缺資料</p>
        : <p style={{ margin: 0, color: metric.color, fontWeight: 600 }}>{metric.formatter(payload[0].value)}</p>
      }
    </div>
  );
};

const TemperatureChart = ({
  data,
  selectedDay,
  dailyData,
  onDayChange,
  onCrossDayRequest,
  daysInMonth = 30,
  year,
  month,
}) => {
  const [viewMode, setViewMode]     = useState('day');
  const [dayOffset, setDayOffset]   = useState(0);
  const [chartMetric, setChartMetric] = useState('temperature');
  const [crossDayData, setCrossDayData] = useState([]);

  const metric = METRIC_CONFIG[chartMetric];
  const currentDay = selectedDay + dayOffset;

  // 保持最新的 callback 引用，避免 effect 依賴頻繁觸發
  const crossDayRequestRef = useRef(onCrossDayRequest);
  useEffect(() => { crossDayRequestRef.current = onCrossDayRequest; }, [onCrossDayRequest]);

  // 切換至跨日模式或換日時，從 API 取資料
  useEffect(() => {
    if (viewMode !== 'crossday') return;
    const startDay = Math.max(1, currentDay);
    const endDay   = Math.min(daysInMonth, startDay + 1);
    crossDayRequestRef.current?.(startDay, endDay).then(setCrossDayData);
  }, [viewMode, currentDay, daysInMonth]);

  // 切換月份/selectedDay 時重置 offset 和跨日資料
  useEffect(() => {
    setDayOffset(0);
    setCrossDayData([]);
  }, [selectedDay, year, month]);

  const chartData = viewMode === 'day' ? data : crossDayData;

  // 插值填補 null（僅用於畫線），並標記 _missing 供 tooltip 識別
  const processedChartData = (() => {
    if (!chartData.length) return chartData;
    const key = metric.dataKey;
    const result = chartData.map(d => ({ ...d }));
    for (let i = 0; i < result.length; i++) {
      if (result[i][key] == null) {
        let prev = null, next = null;
        for (let j = i - 1; j >= 0; j--) if (result[j][key] != null) { prev = result[j][key]; break; }
        for (let j = i + 1; j < result.length; j++) if (result[j][key] != null) { next = result[j][key]; break; }
        result[i][key] = prev != null && next != null ? (prev + next) / 2 : (prev ?? next ?? 0);
        result[i]._missing = true;
      }
    }
    return result;
  })();

  const handlePrevDay = () => {
    if (currentDay <= 1) return;
    if (viewMode === 'day') onDayChange(selectedDay - 1);
    else setDayOffset(o => o - 1);
  };
  const handleNextDay = () => {
    if (currentDay >= daysInMonth) return;
    if (viewMode === 'day') onDayChange(selectedDay + 1);
    else setDayOffset(o => o + 1);
  };

  if (!data || data.length === 0) {
    return <div className="chart-container">請選擇日期以查看趨勢</div>;
  }

  return (
    <div className="chart-container">
      <div className="chart-header">
        <h2>
          {viewMode === 'day'
            ? `${month}月 ${selectedDay}日 ${metric.label}折線圖`
            : `${month}月 ${currentDay}–${Math.min(currentDay + 1, daysInMonth)}日 ${metric.label}趨勢`}
        </h2>

        <div className="chart-controls">
          <div className="view-mode-toggle">
            <button className={`mode-btn ${viewMode === 'day' ? 'active' : ''}`}
              onClick={() => { setViewMode('day'); setDayOffset(0); }}>
              單日檢視
            </button>
            <button className={`mode-btn ${viewMode === 'crossday' ? 'active' : ''}`}
              onClick={() => { setViewMode('crossday'); setDayOffset(0); }}>
              跨日檢視
            </button>
          </div>

          <div className="view-mode-toggle">
            {Object.entries(METRIC_CONFIG).map(([key, cfg]) => (
              <button key={key}
                className={`mode-btn ${chartMetric === key ? 'active' : ''}`}
                style={chartMetric === key ? { background: cfg.color, boxShadow: `0 2px 8px ${cfg.color}66` } : {}}
                onClick={() => setChartMetric(key)}>
                {cfg.label}
              </button>
            ))}
          </div>

          <div className="day-navigation">
            <button className="nav-btn" onClick={handlePrevDay} disabled={currentDay <= 1}>← 前一天</button>
            <span className="day-display">
              {viewMode === 'day' ? `${selectedDay}日` : `${currentDay}–${Math.min(currentDay + 1, daysInMonth)}日`}
            </span>
            <button className="nav-btn" onClick={handleNextDay} disabled={currentDay >= daysInMonth}>後一天 →</button>
          </div>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={processedChartData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="hour" tick={{ fontSize: 12 }} interval={Math.max(0, Math.floor(chartData.length / 10))} />
          <YAxis domain={metric.domain} label={{ value: metric.yAxisLabel, angle: -90, position: 'insideLeft' }} />
          <Tooltip content={<CustomTooltip metric={metric} />} />
          <Legend />
          <Line type="monotone" dataKey={metric.dataKey} stroke={metric.color}
            dot={false} strokeWidth={2} name={metric.label} isAnimationActive={true}
            />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default TemperatureChart;
