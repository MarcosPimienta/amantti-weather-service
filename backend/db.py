import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.models import WeatherLog, Base
from datetime import datetime
from typing import List

# Support DATABASE_URL environment variable for production
# Falls back to SQLite for local development
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./weather.db")

# Handle SQLite-specific configuration
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # For PostgreSQL and other databases
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Called once to create tables
def init_db():
  Base.metadata.create_all(bind=engine)


def save_weather_data(db: Session, data: List[dict]) -> None:
  for entry in data:
    log = WeatherLog(
      town=entry["town"],
      temperature=entry["temperature"],
      humidity=entry["humidity"],
      rainfall=entry["rainfall"],
      rain_alert=entry["rain_alert"],
      mold_risk=entry["mold_risk"],
      alert=entry["alert"],
      timestamp=datetime.fromisoformat(entry["timestamp"])
    )
    db.add(log)
  db.commit()