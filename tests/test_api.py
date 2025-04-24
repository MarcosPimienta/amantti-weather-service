from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_results_endpoint_returns_expected_keys():
  response = client.get("/results")
  assert response.status_code == 200
  data = response.json()

  assert "summary" in data
  assert "alerts" in data
  assert isinstance(data["summary"], dict)
  assert isinstance(data["alerts"], list)
