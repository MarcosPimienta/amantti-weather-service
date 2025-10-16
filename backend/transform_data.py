from statistics import mean
from typing import List, Dict

def transform_weather_data(data: List[Dict[str, any]]) -> Dict[str, any]:
  if not data:
    return {
      "summary": {},
      "details": [],
    }

  temperatures = [item["temperature"] for item in data]
  humidities = [item["humidity"] for item in data]

  summary = {
    "average_temperature": round(mean(temperatures), 2),
    "average_humidity": round(mean(humidities), 2),
    "total_towns": len(data),
  }

  # Thresholds
  RAIN_THRESHOLD = 10.0  # mm/h
  HUMIDITY_THRESHOLD = 95  # %

  detailed_results = []
  for item in data:
    rain_alert = item["rainfall"] >= RAIN_THRESHOLD
    mold_risk = item["humidity"] >= HUMIDITY_THRESHOLD

    item["rain_alert"] = rain_alert
    item["mold_risk"] = mold_risk
    item["alert"] = rain_alert or mold_risk

    detailed_results.append(item)

  return {
    "summary": summary,
    "details": detailed_results,
  }
