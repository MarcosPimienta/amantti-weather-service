# 🌤️ Amantti Weather Insight Microservice

This asynchronous Python microservice fetches real-time weather data for key coffee-sourcing towns in Antioquia, Colombia. It calculates average conditions, flags anomalies like excess rainfall or extreme humidity, and stores this data for analysis.

---

## 🚀 Features

- 🔄 **Asynchronous data fetching** using `httpx` and `asyncio`
- 📡 Fetches data from OpenWeatherMap API for towns like Andes, Jardín, Betania, Urrao, etc.
- 📊 Calculates average temperature and humidity
- ⚠️ Flags anomalies such as:
  - Rainfall over 10mm/hour
  - Humidity above 95% (mold risk)
- 🧠 Data transformation using built-in Python modules
- 🗃️ Data storage in SQLite using SQLAlchemy ORM
- ⚡ FastAPI-powered REST API:
  - `GET /fetch_data` — fetch, process, and store new data
  - `GET /results` — view latest insights and alerts

---

## 📦 Requirements

Install dependencies:

```bash
pip install -r requirements.txt
```

## ⚙️ Environment Variables

Create a .env file in the project root with the following content:
```
WEATHER_API_KEY=your_openweathermap_key
```

## 🛠️ Running the Service

Start the FastAPI server with:
```
uvicorn app.main:app --reload
```

## 🔌 API Endpoints

GET /fetch_data
Triggers weather data fetch, transformation, and database storage

Returns summary statistics and per-town alert flags

GET /results
Returns most recent weather data and aggregated metrics

Useful for quick monitoring and decision making

## 🕹️ Interactive API Docs
Access the FastAPI auto-generated docs here: http://localhost:8000/docs

## ⚗️ Testing

Run the test suite with:
```
pytest
```
Tests are located in the tests/ folder:

- test_transform.py — validates alert logic for rain/mold

- test_api.py — tests response structure of the /results endpoint

## 📂 Project Structure
```
amantti-weather-service/
├── app/
│   ├── main.py           # FastAPI app
│   ├── api.py            # Routes
│   ├── weather.py        # Weather logic
│   ├── models.py         # DB models
│   ├── db.py             # DB connection
│   ├── locations.py      # JSON locations
│   ├── config.py         # Env vars
|   └── transform_data.py # Transforms fetched data
├── tests/
│   ├── test_api.py
|   └── test_transform.py
├── .env
├── requirements.txt
├── README.md
```

## 🧠 Design Decisions
* FastAPI for async capabilities and automatic documentation
* httpx for modern, non-blocking HTTP requests
* SQLAlchemy for simple, robust ORM interaction
* Separation of Concerns:
    * weather.py: fetch-only logic
    * transform_data.py: alert logic and transformation
    * db.py: handles persistence
* No pandas required: all transformations use lightweight built-in modules
