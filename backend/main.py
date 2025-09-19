# backend/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # Ensure this import is here
from app.api.v1.router import api_router

app = FastAPI(
    title="Magento AI Operator",
    version="1.0.0",
)

# --- START: CORS CONFIGURATION ---

# Define the list of allowed origins.
# For development, this includes your Next.js and potentially other frontends.
origins = [
    "http://localhost:3000",  # Your Next.js frontend
    "http://localhost:5173",  # The old Vite frontend, just in case
]

# Add the CORSMiddleware to your application
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # List of origins that are allowed to make requests
    allow_credentials=True,  # Allow cookies to be included in requests
    allow_methods=["*"],     # Allow all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],     # Allow all headers
)

# --- END: CORS CONFIGURATION ---


# Include the API router
app.include_router(api_router, prefix="/api/v1")

@app.get("/", tags=["Health Check"])
def read_root():
    return {"status": "ok", "message": "Welcome to the Magento AI Operator API"}