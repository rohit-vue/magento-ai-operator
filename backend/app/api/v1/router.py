# backend/app/api/v1/router.py
from fastapi import APIRouter
from app.api.v1.endpoints import chatbot, files, auth # <--- IMPORT auth

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"]) # <--- ADD THIS LINE
api_router.include_router(chatbot.router, prefix="/chatbot", tags=["Chatbot"])
api_router.include_router(files.router, prefix="/files", tags=["File Operations"])