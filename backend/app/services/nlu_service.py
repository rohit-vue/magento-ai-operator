# backend/app/services/nlu_service.py
import json
from openai import AsyncOpenAI
from app.core.config import settings

# Initialize the Async OpenAI client
client = AsyncOpenAI(api_key=settings.LLM_API_KEY)

# Define the functions our chatbot can perform
tools = [
    {
        "type": "function",
        "function": {
            "name": "create_product",
            "description": "Creates a new simple product in Magento.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name of the product, e.g., 'Fusion Backpack'",
                    },
                    "sku": {
                        "type": "string",
                        "description": "The unique Stock Keeping Unit, e.g., 'FUSION-BP-01'",
                    },
                    "price": {
                        "type": "number",
                        "description": "The price of the product, e.g., 59.99",
                    },
                },
                "required": ["name", "sku", "price"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_status",
            "description": "Gets the current status of a specific order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The unique ID of the order, e.g., '000000123'",
                    },
                },
                "required": ["order_id"],
            },
        },
    },

     {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Extracts all search criteria from a user's query about finding products.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": { "type": "string", "description": "Any general keywords from the prompt, like 'pendant light' or a SKU." },
                    "brand": { "type": "string", "description": "Any brand name mentioned, e.g., 'Access Lighting'." },
                    "attributes": {
                        "type": "array",
                        "description": "Any specific product characteristic mentioned. For 'dimmable lights', extract {'key': 'dimmable', 'value': 'dimmable'}. For 'lights with an Opal shade finish', extract {'key': 'Shade Finish', 'value': 'Opal'}.",
                        "items": { "type": "object", "properties": { "key": {"type": "string"}, "value": {"type": "string"} } }
                    },
                },
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "aggregate_products",
            "description": "Counts products based on a specific, structured filter. Use this ONLY when the user explicitly asks to count items in a specific CATEGORY or with a specific ATTRIBUTE value.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filter_by": {
                        "type": "object",
                        "description": "The specific criteria to filter products by before counting.",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "The name of a product category, like 'Accessories', 'Men', or 'Electronics'. Do not use this for general search terms.",
                            },
                            "attribute": {
                                "type": "object",
                                "description": "A specific attribute key-value pair, e.g., {'key': 'manufacturer', 'value': 'Ortech'}.",
                                "properties": {
                                    "key": {"type": "string"},
                                    "value": {"type": "string"},
                                },
                            },
                        },
                    },
                },
                "required": ["filter_by"],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "check_inventory",
            "description": "Checks the stock quantity for a specific product SKU.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sku": {
                        "type": "string",
                        "description": "The exact SKU of the product to check inventory for, e.g., '89123-OPL'.",
                    },
                },
                "required": ["sku"],
            },
        },
    },


]

async def classify_intent(user_message: str) -> dict:
    """
    Uses the LLM to classify the user's intent and extract parameters.
    """
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
            # The LLM decided a function should be called
            tool_call = tool_calls[0]
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            return {
                "intent": function_name,
                "parameters": function_args
            }
        else:
            # The LLM did not identify a specific function to call
            return {"intent": "general_conversation", "parameters": {}}
        
    

    except Exception as e:
        print(f"Error in LLM classification: {e}")
        return {"intent": "error", "parameters": {"details": str(e)}}
    
async def choose_best_option(user_query: str, attribute_name: str, options: list[str]) -> str:
    """A second AI call to choose the best option from a list."""
    client = AsyncOpenAI(api_key=settings.LLM_API_KEY)
    
    prompt = (
        f"The user wants to filter by the attribute '{attribute_name}' with the query: '{user_query}'.\n"
        f"The only available options for '{attribute_name}' are: {', '.join(options)}.\n"
        f"Which of these is the best fit for the user's request? Please respond with only the single best option text."
    )
    
    response = await client.chat.completions.create(
        model=settings.LLM_MODEL_NAME, # Or a cheaper/faster model like gpt-3.5-turbo
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0
    )
    return response.choices[0].message.content.strip()