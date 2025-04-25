from app.transform_data import transform_weather_data

def test_transform_weather_data_flags_alerts():
  mock_data = [
    {
      "town": "Test Town",
      "temperature": 22.5,
      "humidity": 97,
      "rainfall": 12.0,
      "timestamp": "2024-04-20T10:00:00"
    }
  ]

  result = transform_weather_data(mock_data)

  assert result["summary"]["average_temperature"] == 22.5
  assert result["details"][0]["rain_alert"] is True
  assert result["details"][0]["mold_risk"] is True
  assert result["details"][0]["alert"] is True
