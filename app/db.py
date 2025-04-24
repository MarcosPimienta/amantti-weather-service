from sqlalchemy import create_engine, Session
from sqlalchemy.orm import sessionmaker, WeatherLog
from app.models import Base
from datetime import datetime
from types import List

DATABASE_URL = "sqlite:///./weather.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
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