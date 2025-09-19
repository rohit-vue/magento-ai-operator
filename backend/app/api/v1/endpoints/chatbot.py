# backend/app/api/v1/endpoints/chatbot.py
from fastapi import APIRouter
from app.schemas.chatbot import ChatRequest, ChatResponse
from app.services.nlu_service import classify_intent
from app.services.magento_wrapper import magento_service

router = APIRouter()

@router.post("/chat")
async def handle_chat(request: ChatRequest):
    if not request.credentials:
        return ChatResponse(response_text="Please connect to a store first.")

    params = await classify_intent(request.message)
    
    if params.get("task") == "error":
        return ChatResponse(response_text="Sorry, I had trouble understanding your request.")

    task = params.get("task")
    
    try:
        # Call the one and only search function with all extracted params
        result = magento_service.product_search(
            keywords=params.get("keywords"),
            brand=params.get("brand"),
            filters=params.get("filters"),
            count_only=(task == "count"),
            limit=params.get("limit", 10),
            credentials=request.credentials.dict()
        )
        
        if task == "count":
            count = result.get("total_count", 0)
            return ChatResponse(response_text=f"I found a total of {count} products matching your criteria.")
        
        else: # Search task
            products = result.get("items", [])
            total_count = result.get("total_count", 0)
            if not products:
                return ChatResponse(response_text="I couldn't find any products matching your search.")
            
            response_text = f"Here are the top {len(products)} of {total_count} results:"
            return ChatResponse(response_text=response_text, intent="search_products_result", data=products)

    except Exception as e:
        return ChatResponse(response_text=f"An error occurred: {e}")