import os
import httpx
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
from config import get_settings

settings = get_settings()

BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

async def fetch_weather(client: httpx.AsyncClient, town: Dict[str, any]) -> Optional[Dict[str, any]]:
  try:
    response = await client.get(
      BASE_URL,
      params={
        "lat": town["lat"],
        "lon": town["lon"],
        "appid": settings.WEATHER_API_KEY,
        "units": "metric"
      },
      timeout=10
    )
    response.raise_for_status()
    data = response.json()

    return {
      "town": town["name"],
      "temperature": data["main"]["temp"],
      "humidity": data["main"]["humidity"],
      "rainfall": data.get("rain", {}).get("1h", 0.0),
      "timestamp": datetime.utcfromtimestamp(data["dt"]).isoformat()
    }

  except httpx.RequestError as exc:
      print(f"⚠️ Network error while fetching {town['name']}: {exc}")
  except httpx.HTTPStatusError as exc:
      print(f"❌ HTTP error while fetching {town['name']}: {exc.response.status_code}")
  except KeyError as exc:
      print(f"🔑 Key missing in response for {town['name']}: {exc}")

  return None


async def fetch_all_weather(towns: List[Dict[str, any]]) -> List[Dict[str, any]]:
  results = []
  async with httpx.AsyncClient() as client:
    tasks = [fetch_weather(client, town) for town in towns]
    responses = await asyncio.gather(*tasks)
    results = [res for res in responses if res is not None]
  return results
