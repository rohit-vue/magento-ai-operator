# backend/app/api/v1/endpoints/chatbot.py
from fastapi import APIRouter
from app.schemas.chatbot import ChatRequest, ChatResponse
from app.services.nlu_service import classify_intent
from app.services.magento_wrapper import magento_service
from app.services.nlu_service import choose_best_option
import json

router = APIRouter()

@router.post("/chat")
async def handle_chat(request: ChatRequest):
    if not request.credentials:
        return ChatResponse(response_text="Please connect to a store first.", intent="error")

    # Step 1: Get the structured search parameters from the AI
    classified = await classify_intent(request.message)
    intent = classified.get("intent")
    params = classified.get("parameters", {})

    if intent == "search_products":
        search_criteria = params
        if not search_criteria:
            return ChatResponse(response_text="Please tell me what you're looking for.", intent="info")

        try:
            # Step 2: Pass the parameters directly to the powerful search function
            products = magento_service.search_products(search_criteria, request.credentials.dict())
            
            if not products:
                search_desc_parts = []
                for k, v in search_criteria.items():
                    if k == 'attributes':
                        attrs_str = ", ".join([f"{attr['key']}='{attr['value']}'" for attr in v])
                        search_desc_parts.append(attrs_str)
                    else:
                        search_desc_parts.append(f"{k}='{v}'")
                search_desc = " and ".join(search_desc_parts)
                response_text = f"I couldn't find any products matching your criteria: {search_desc}."
                return ChatResponse(response_text=response_text)

            response_text = f"Here are the top {len(products)} results for your search:"
            return ChatResponse(response_text=response_text, intent="search_products_result", data=products)
        except Exception as e:
            return ChatResponse(response_text=f"An error occurred: {e}", intent="error")
    
    # You can add logic for the 'aggregate_products' intent here if you want to use it
    # elif intent == "aggregate_products":
    #     ...

    else: # Fallback
        return ChatResponse(response_text="I can help you search for products. What are you looking for?")