# backend/app/schemas/chatbot.py
from pydantic import BaseModel
from typing import Optional, Any

# 1. ADD THIS NEW MODEL to define the shape of the credentials object
class MagentoCredentials(BaseModel):
    store_url: str
    consumer_key: str
    consumer_secret: str
    access_token: str
    access_token_secret: str

# 2. MODIFY the ChatRequest model
class ChatRequest(BaseModel):
    user_id: str
    session_id: str
    message: str
    # This is the crucial new line. It's optional so that
    # requests made before connection don't cause errors.
    credentials: Optional[MagentoCredentials] = None

# 3. MODIFY the ChatResponse model to explicitly allow lists for search results
class ChatResponse(BaseModel):
    response_text: str
    intent: Optional[str] = None
    # Using 'Any' is a robust way to allow dictionaries OR lists
    data: Optional[Any] = None