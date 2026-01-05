from fastapi import FastAPI
from app.db import init_db
from app.api import router

init_db()

app = FastAPI()

app.include_router(router)