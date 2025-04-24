from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.locations import TOWNS
from app.weather import fetch_all_weather
from app.transform_data import transform_weather_data
from app.db import SessionLocal, save_weather_data
from app.models import WeatherLog

from fastapi.responses import JSONResponse

router = APIRouter()

def get_db():
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()

@router.get("/fetch_data")
async def fetch_data(db: Session = Depends(get_db)):
  raw_data = await fetch_all_weather(TOWNS)
  transformed = transform_weather_data(raw_data)
  save_weather_data(db, transformed["details"])
  return JSONResponse(content=transformed)

@router.get("/results")
def get_latest_results(db: Session = Depends(get_db)):
  logs = db.query(WeatherLog).order_by(WeatherLog.timestamp.desc()).limit(15).all()

  alerts = [
    {
      "town": log.town,
      "temperature": log.temperature,
      "humidity": log.humidity,
      "rainfall": log.rainfall,
      "alert": log.alert,
      "timestamp": log.timestamp.isoformat()
    }
    for log in logs if log.alert
  ]

  avg_temp = round(sum(log.temperature for log in logs) / len(logs), 2) if logs else None
  avg_humidity = round(sum(log.humidity for log in logs) / len(logs), 2) if logs else None

  return {
    "summary": {
      "average_temperature": avg_temp,
      "average_humidity": avg_humidity,
      "total_records": len(logs),
    },
    "alerts": alerts
  }
