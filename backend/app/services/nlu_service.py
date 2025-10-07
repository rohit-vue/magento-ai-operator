# backend/app/services/nlu_service.py
import json
from openai import AsyncOpenAI
from app.core.config import settings

client = AsyncOpenAI(api_key=settings.LLM_API_KEY)

# A simple tool that can distinguish brand from keywords
tools = [
    {
        "type": "function",
        "function": {
            "name": "product_search",
            "description": "Extracts keywords and a brand name from a user's product search query to find or count products.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "string",
                        "description": "Any general keywords, product names, or SKUs from the prompt. For 'show me Bazz recessed lights', this would be 'recessed lights'.",
                    },
                    "brand": {
                        "type": "string",
                        "description": "The brand name mentioned, if any. For 'show me Bazz recessed lights', this would be 'Bazz'.",
                    },
                },
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
            # The intent is always product_search, we just need the arguments
            return json.loads(tool_calls[0].function.arguments)
        else:
            # If the AI fails, treat the whole message as keywords
            return {"keywords": user_message}
    except Exception as e:
        print(f"Error in LLM classification: {e}")
        return {"error": str(e)}