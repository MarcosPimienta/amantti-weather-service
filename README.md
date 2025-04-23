# 🌤️ Amantti Weather Insight Microservice

This asynchronous Python microservice fetches real-time weather data for key coffee-sourcing towns in Antioquia, Colombia. It calculates average conditions, flags anomalies like excess rainfall or extreme humidity, and stores this data for analysis.

---

## 🚀 Features

- Asynchronous weather data fetching using `httpx` and `asyncio`
- Real-time insights for towns like Andes, Jardín, Betania, Salgar, and Urrao
- Pandas-based transformation to calculate averages and detect weather anomalies
- Data stored in a local SQLite database using SQLAlchemy ORM
- FastAPI-based RESTful API with two endpoints:
  - `GET /fetch_data`: Fetch, transform, and store weather data
  - `GET /results`: Retrieve summary of latest weather insights

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

## ⚗️ Testing

Run the test suite with:
```
pytest
```
Tests are located in the tests/ folder and validate data transformation and API behavior.

## 📂 Project Structure
```
amantti-weather-service/
├── app/
│   ├── main.py           # FastAPI app
│   ├── api.py            # Routes
│   ├── weather.py        # Weather logic
│   ├── models.py         # DB models
│   ├── db.py             # DB connection
│   └── config.py         # Env vars
├── tests/
├── .env
├── requirements.txt
├── README.md
```

## ✨ Design Highlights
- Built for real-world use by Amantti Coffee to monitor growing conditions
- Enables data-driven logistics and harvest planning
- Built entirely with async Python and minimal dependencies
