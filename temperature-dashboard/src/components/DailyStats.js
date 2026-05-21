import React from 'react';
import './DailyStats.css';

const DailyStats = ({ dailyData, selectedDay, onDaySelect, year, month }) => {
  const weeks = [];
  const firstDayOfWeek = new Date(year, month - 1, 1).getDay();

  const firstWeek = new Array(firstDayOfWeek).fill(null);
  for (let i = 0; i < dailyData.length; i++) {
    firstWeek.push(dailyData[i]);
    if (firstWeek.length === 7) { weeks.push([...firstWeek]); firstWeek.length = 0; }
  }
  if (firstWeek.length > 0) weeks.push(firstWeek);

  const weekLabels = ['日', '一', '二', '三', '四', '五', '六'];

  return (
    <div className="daily-stats-container">
      <h2>{year}年{month}月 氣溫日曆</h2>
      
      {/* Week day headers */}
      <div className="calendar">
        <div className="week-header">
          {weekLabels.map((label) => (
            <div key={label} className="week-label">
              星期{label}
            </div>
          ))}
        </div>

        {/* Calendar grid */}
        {weeks.map((week, weekIndex) => (
          <div key={weekIndex} className="calendar-week">
            {week.map((day, dayIndex) => (
              <div
                key={dayIndex}
                className={`calendar-day ${day ? (selectedDay === day.day ? 'selected' : '') : 'empty'}`}
                onClick={() => day && onDaySelect(day.day)}
              >
                {day ? (
                  <>
                    <div className="day-number">
                      {day.dayString}日
                    </div>
                    <div className="weather-icon">
                      {day.weather.icon}
                    </div>
                    <div className="temp-info">
                      <div className="max-temp">
                        ↑{day.maxTemp.toFixed(1)}°
                      </div>
                      <div className="min-temp">
                        ↓{day.minTemp.toFixed(1)}°
                      </div>
                    </div>
                  </>
                ) : null}
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
};

export default DailyStats;
