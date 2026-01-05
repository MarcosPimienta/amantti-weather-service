from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
  WEATHER_API_KEY: str = os.getenv("WEATHER_API_KEY")

def get_settings():
  return Settings()