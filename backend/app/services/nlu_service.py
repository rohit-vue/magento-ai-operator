# backend/app/services/nlu_service.py
import json
from openai import AsyncOpenAI
from app.core.config import settings

client = AsyncOpenAI(api_key=settings.LLM_API_KEY)

tools = [
    {
        "type": "function",
        "function": {
            "name": "product_query",
            "description": "Extracts all criteria from a user's request to find or count products.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": { "type": "string", "enum": ["search", "count"], "description": "The user's goal: 'search' to list products, 'count' for 'how many'." },
                    "keywords": { "type": "string", "description": "General search terms, SKUs, or descriptive text like 'recessed light' or 'Type-IC'." },
                    "brand": { "type": "string", "description": "The brand name mentioned, e.g., 'Access Lighting'." },
                    "filters": {
                        "type": "array",
                        "description": "Special conditions. For 'on sale' or 'special prices', extract {'key': 'on_sale', 'value': 'true'}.",
                        "items": { "type": "object", "properties": { "key": {"type": "string"}, "value": {"type": "string"} } }
                    },
                    "limit": { "type": "integer", "description": "The number of products to return, e.g., 'show me 5 products' -> 5." }
                },
                "required": ["task"],
            },
        },
    }
]

async def classify_intent(user_message: str) -> dict:
    try:
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=[{"role": "user", "content": user_message}],
            tools=tools,
            tool_choice="auto",
        )
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        if tool_calls:
            return json.loads(tool_calls[0].function.arguments)
        else:
            return {"task": "search", "keywords": user_message}
    except Exception as e:
        print(f"Error in LLM classification: {e}")
        return {"task": "error", "details": str(e)}