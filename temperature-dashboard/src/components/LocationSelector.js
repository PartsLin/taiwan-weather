import React from 'react';
import './LocationSelector.css';

const LocationSelector = ({ county, district, counties, districts, onCountyChange, onDistrictChange }) => (
  <div className="location-selector">
    <span className="location-icon">📍</span>
    <select
      className="location-select"
      value={county}
      onChange={e => onCountyChange(e.target.value)}
    >
      {counties.map(c => (
        <option key={c} value={c}>{c}</option>
      ))}
    </select>
    <span className="location-divider">›</span>
    <select
      className="location-select"
      value={district}
      onChange={e => onDistrictChange(e.target.value)}
      disabled={districts.length === 0}
    >
      {districts.map(d => (
        <option key={d} value={d}>{d}</option>
      ))}
    </select>
  </div>
);

export default LocationSelector;
