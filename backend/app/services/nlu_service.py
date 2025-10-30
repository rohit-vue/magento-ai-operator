# backend/app/services/nlu_service.py
import json
from openai import AsyncOpenAI
from app.core.config import settings
from typing import Any

client = AsyncOpenAI(api_key=settings.LLM_API_KEY)

tools = [
    {
        "type": "function",
        "function": {
            "name": "product_query",
            "description": "The primary tool to handle any user request about finding, counting, or getting details about products.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": { "type": "string", "enum": ["search", "count", "details"]},
                    "keywords": { "type": "string", "description": "The main subject of the user's search, like 'LED bulb' or 'pendant lights'."},
                    "sku": { "type": "string", "description": "The specific product SKU, if mentioned."},
                    "brand": { "type": "string", "description": "The brand name, if mentioned."},
                    # --- NEW PARAMETER ---
                    "category": {
                        "type": "string",
                        "description": "The product category or subcategory name, if mentioned by the user. e.g., 'Outdoor Lighting'."
                    },
                    "question": { "type": "string", "description": "The user's specific question if the task is 'details'."},
                    "on_sale": { "type": "boolean", "description": "Set to true for products on sale or with special prices."},
                    "limit": { "type": "integer", "description": "The number of products to return."},
                    "attributes": { "type": "object", "description": "A dictionary of specific product attributes to filter by."}
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
            tool_choice={"type": "function", "function": {"name": "product_query"}}
        )
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        if tool_calls:
            arguments = json.loads(tool_calls[0].function.arguments)
            # Cleanup empty values
            for key in ["attributes", "keywords", "category"]:
                if key in arguments and not arguments[key]:
                    del arguments[key]
            return arguments
        else:
            return {"task": "search", "keywords": user_message}
    except Exception as e:
        print(f"Error in LLM classification: {e}")
        return {"task": "error", "details": str(e)}