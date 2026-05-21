const getDayOfWeek = (day) => {
  const firstDayOfMonth = 3; // 2026年4月1日是星期三
  return (firstDayOfMonth + (day - 1)) % 7;
};

const weekDays = ['日', '一', '二', '三', '四', '五', '六'];

// 依中央氣象署標準推算天氣現象
// 雲量採 0–10 制：0–2 晴、3–7 多雲、8–10 陰
// 降水時數：>0 有雨、>6 整日陰雨
const inferWeather = (hourlyTemps, cloudAmount, sunshineHours, precipitationHours) => {
  const validCloud = cloudAmount.filter(c => c !== '--' && !isNaN(parseFloat(c)));
  const avgCloud = validCloud.length > 0
    ? validCloud.reduce((a, b) => a + parseFloat(b), 0) / validCloud.length
    : 5;

  const totalPrecip = precipitationHours
    .filter(p => p !== '--' && !isNaN(parseFloat(p)))
    .reduce((a, b) => a + parseFloat(b), 0);

  if (totalPrecip > 6) return { type: 'heavy-rain', icon: '🌧️', label: '陰雨' };
  if (totalPrecip > 0) {
    if (avgCloud >= 8) return { type: 'cloudy-rain', icon: '🌦️', label: '陰有雨' };
    return { type: 'shower', icon: '🌦️', label: '短暫雨' };
  }

  if (avgCloud < 3) return { type: 'sunny', icon: '☀️', label: '晴天' };
  if (avgCloud < 8) return { type: 'partly-cloudy', icon: '⛅', label: '多雲' };
  return { type: 'overcast', icon: '☁️', label: '陰天' };
};

export const parseTemperatureData = (csvText, cloudData, sunshineData, precipitationData) => {
  const lines = csvText.trim().split('\n');
  const hourLabels = lines[0].split(',').map(h => h.replace(/"/g, ''));
  const dailyData = [];

  for (let i = 1; i < lines.length - 1; i++) {
    const row = lines[i].split(',').map(val => val.replace(/"/g, ''));
    const day = row[0];
    const dayNum = parseInt(day);

    const hourlyTemps = row.slice(1, -1).map(temp => parseFloat(temp));
    const maxTemp = Math.max(...hourlyTemps);
    const minTemp = Math.min(...hourlyTemps);
    const avgTemp = (hourlyTemps.reduce((a, b) => a + b, 0) / hourlyTemps.length).toFixed(1);

    const cloud = cloudData[dayNum] || [];
    const sunshine = sunshineData[dayNum] || [];
    const precipitation = precipitationData[dayNum] || [];
    
    const dayOfWeek = getDayOfWeek(dayNum);
    const weather = inferWeather(hourlyTemps, cloud, sunshine, precipitation);

    const validCloud = cloud.filter(c => c !== '--' && !isNaN(parseFloat(c)));
    const avgCloud = validCloud.length > 0
      ? validCloud.reduce((a, b) => a + parseFloat(b), 0) / validCloud.length
      : null;
    const dailySunshine = sunshine.filter(s => !isNaN(parseFloat(s))).reduce((a, b) => a + parseFloat(b), 0);
    const dailyPrecipitation = precipitation.filter(p => !isNaN(parseFloat(p))).reduce((a, b) => a + parseFloat(b), 0);

    dailyData.push({
      day: dayNum,
      dayString: day,
      maxTemp,
      minTemp,
      avgTemp: parseFloat(avgTemp),
      hourlyTemps,
      hourlySunshine: sunshine,
      hourlyPrecipitation: precipitation,
      hourLabels: hourLabels.slice(1, -1),
      weekDay: weekDays[dayOfWeek],
      weekDayNum: dayOfWeek,
      weather,
      cloudAmount: avgCloud,
      sunshineHours: dailySunshine,
      precipitationHours: dailyPrecipitation
    });
  }
  
  return dailyData;
};

export const getDailyHourlyData = (dailyData, dayNumber) => {
  const day = dailyData.find(d => d.day === dayNumber);
  if (!day) return [];

  return day.hourLabels.map((hour, index) => ({
    hour: `${hour}:00`,
    temperature: day.hourlyTemps[index],
    sunshine: parseFloat(day.hourlySunshine[index]) || 0,
    precipitation: parseFloat(day.hourlyPrecipitation[index]) || 0,
  }));
};

// ── API 資料轉換 ──────────────────────────────────────────

const _weekDays = ['日', '一', '二', '三', '四', '五', '六'];

const inferWeatherFromSummary = (avgCloud, totalPrecip) => {
  const cloud = avgCloud ?? 5;
  const precip = totalPrecip ?? 0;
  if (precip > 6) return { type: 'heavy-rain', icon: '🌧️', label: '陰雨' };
  if (precip > 0) {
    if (cloud >= 8) return { type: 'cloudy-rain', icon: '🌦️', label: '陰有雨' };
    return { type: 'shower', icon: '🌦️', label: '短暫雨' };
  }
  if (cloud < 3) return { type: 'sunny', icon: '☀️', label: '晴天' };
  if (cloud < 8) return { type: 'partly-cloudy', icon: '⛅', label: '多雲' };
  return { type: 'overcast', icon: '☁️', label: '陰天' };
};

export const transformApiDailyData = (rows, year, month) =>
  rows.map(row => {
    const dayNum = parseInt(row.obs_date.slice(8, 10), 10);
    const dow = new Date(year, month - 1, dayNum).getDay();
    return {
      day: dayNum,
      dayString: String(dayNum).padStart(2, '0'),
      maxTemp: row.max_temp,
      minTemp: row.min_temp,
      avgTemp: row.avg_temp,
      weekDay: _weekDays[dow],
      weekDayNum: dow,
      weather: inferWeatherFromSummary(row.avg_cloud, row.total_precipitation),
      cloudAmount: row.avg_cloud,
      sunshineHours: row.total_sunshine ?? 0,
      precipitationHours: row.total_precipitation ?? 0,
      avgHumidity: row.avg_humidity,
      hourlyTemps: [],
      hourlySunshine: [],
      hourlyPrecipitation: [],
      hourLabels: [],
    };
  });

export const transformApiHourlyData = (rows, crossDay = false) =>
  rows.map(row => {
    const dayNum = parseInt(row.obs_date.slice(8, 10), 10);
    return {
      hour: crossDay
        ? `${dayNum}日${String(row.obs_hour).padStart(2, '0')}:00`
        : `${row.obs_hour}:00`,
      temperature: row.temperature,
      sunshine: row.sunshine_duration ?? 0,
      precipitation: row.precipitation_duration ?? 0,
      day: dayNum,
    };
  });
