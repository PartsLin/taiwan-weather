import React from 'react';
import './WeatherDetails.css';

const WeatherDetails = ({ dailyData, selectedDay }) => {
  const dayData = dailyData.find(d => d.day === selectedDay);
  
  if (!dayData) {
    return null;
  }

  return (
    <div className="weather-details">
      <div className="weather-card">
        <div className="weather-icon-large">{dayData.weather.icon}</div>
        <div className="weather-label">{dayData.weather.label}</div>
      </div>
      
      <div className="weather-stats">
        <div className="stat">
          <div className="stat-label">日照</div>
          <div className="stat-value">
            {dayData.sunshineHours.toFixed(1)}
            <span className="stat-unit">小時</span>
          </div>
        </div>

        <div className="stat">
          <div className="stat-label">降水</div>
          <div className="stat-value">
            {dayData.precipitationHours.toFixed(1)}
            <span className="stat-unit">小時</span>
          </div>
        </div>

        <div className="stat">
          <div className="stat-label">雲量</div>
          <div className="stat-value">
            {dayData.cloudAmount !== null ? `${(dayData.cloudAmount * 10).toFixed(0)}%` : '--'}
            <span className="stat-unit"></span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WeatherDetails;
