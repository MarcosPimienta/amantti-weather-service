import sys
import os

# Add the backend directory to Python path so we can import from it
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.db import init_db
from backend.api import router

# Initialize database
init_db()

# Create FastAPI app
app = FastAPI()

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the API router
app.include_router(router)

# Vercel serverless function handler
def handler(request, context):
    """
    Vercel serverless function handler.
    This is called for each request to /api/*
    """
    from mangum import Mangum
    
    asgi_handler = Mangum(app)
    return asgi_handler(request, context)

# For local testing
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
