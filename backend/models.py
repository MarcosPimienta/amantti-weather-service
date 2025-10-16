from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class WeatherLog(Base):
  __tablename__ = "weather_logs"

  id = Column(Integer, primary_key=True, index=True)
  town = Column(String, index=True)
  temperature = Column(Float)
  humidity = Column(Float)
  rainfall = Column(Float)
  rain_alert = Column(Boolean)
  mold_risk = Column(Boolean)
  alert = Column(Boolean)
  timestamp = Column(DateTime)