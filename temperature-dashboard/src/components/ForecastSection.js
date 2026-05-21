import React from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import './ForecastSection.css';

const wxToIcon = (wx) => {
  if (!wx) return '🌡️';
  if (wx.includes('雷')) return '⛈️';
  if (wx.includes('豪雨') || wx.includes('大雨')) return '🌧️';
  if (wx.includes('雨')) return '🌦️';
  if (wx.includes('陰')) return '☁️';
  if (wx.includes('多雲')) return '⛅';
  if (wx.includes('晴')) return '☀️';
  return '🌡️';
};

const dayLabel = (dateStr) => {
  const today    = new Date().toISOString().slice(0, 10);
  const tomorrow = new Date(Date.now() + 86400000).toISOString().slice(0, 10);
  if (dateStr === today)    return '今天';
  if (dateStr === tomorrow) return '明天';
  return null;
};

const ForecastSection = ({ data }) => {
  if (!data?.hourly?.length) return null;

  const { location, hourly } = data;

  // 依日期分組
  const dayMap = {};
  for (const h of hourly) {
    const date = h.dataTime.slice(0, 10);
    if (!dayMap[date]) dayMap[date] = [];
    dayMap[date].push(h);
  }
  const days = Object.entries(dayMap);

  // 折線圖資料
  const chartData = hourly.map(h => ({
    time: `${h.dataTime.slice(5, 10).replace('-', '/')} ${h.dataTime.slice(11, 16)}`,
    temperature: h.temperature,
  }));

  return (
    <div className="forecast-container">
      <h2>
        未來天氣預報
        <span className="forecast-location">{location}</span>
      </h2>

      <div className="forecast-cards">
        {days.map(([date, slots]) => {
          const temps  = slots.map(s => s.temperature).filter(v => v != null);
          const maxT   = temps.length ? Math.max(...temps) : null;
          const minT   = temps.length ? Math.min(...temps) : null;
          const maxPop = Math.max(...slots.map(s => s.pop6h ?? 0));
          const mainWx = slots.find(s => s.wx)?.wx ?? '';
          const mm = date.slice(5, 7);
          const dd = date.slice(8, 10);

          const label = dayLabel(date);
          return (
            <div key={date} className="forecast-card">
              <div className="forecast-date">{label ? `${label} ` : ''}{mm}/{dd}</div>
              <div className="forecast-icon">{wxToIcon(mainWx)}</div>
              <div className="forecast-wx">{mainWx}</div>
              <div className="forecast-temps">
                <span className="forecast-max">↑ {maxT != null ? `${maxT.toFixed(0)}°C` : '--'}</span>
                <span className="forecast-min">↓ {minT != null ? `${minT.toFixed(0)}°C` : '--'}</span>
              </div>
              <div className="forecast-pop">💧 {maxPop}%</div>
            </div>
          );
        })}
      </div>

      <div className="forecast-chart">
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="time" tick={{ fontSize: 10, angle: -40, textAnchor: 'end' }} interval={5} height={48} />
            <YAxis domain={['dataMin - 2', 'dataMax + 2']} tick={{ fontSize: 11 }} />
            <Tooltip formatter={v => `${v}°C`} labelFormatter={l => `時間：${l}`} />
            <Line
              type="monotone"
              dataKey="temperature"
              stroke="#f59f00"
              strokeWidth={2}
              dot={{ r: 3 }}
              name="預報氣溫"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default ForecastSection;
