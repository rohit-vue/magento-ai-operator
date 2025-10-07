# backend/app/schemas/chatbot.py
from pydantic import BaseModel
from typing import Optional, Any

# This model defines the shape of the credentials object
class MagentoCredentials(BaseModel):
    store_url: str
    consumer_key: str
    consumer_secret: str
    access_token: str
    access_token_secret: str

# This is the corrected ChatRequest model
class ChatRequest(BaseModel):
    user_id: str
    message: str
    credentials: Optional[MagentoCredentials] = None
    # vvvvvv THIS IS THE FIX vvvvvv
    context: Optional[Any] = None
    # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

# The response model
class ChatResponse(BaseModel):
    response_text: str
    intent: Optional[str] = None
    data: Optional[Any] = None