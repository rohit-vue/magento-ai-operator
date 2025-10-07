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

    # Step 1: Extract keywords and brand from the user's message.
    params = await classify_intent(request.message)
    
    if params.get("error"):
        return ChatResponse(response_text="Sorry, I had an issue understanding your request.")

    keywords = params.get("keywords")
    brand = params.get("brand")
    
    # Simple check to determine if the user wants to count or search.
    is_counting = "how many" in request.message.lower() or "count" in request.message.lower()

    try:
        # Step 2: Call the one search function with all extracted parameters.
        result = magento_service.product_search(
            keywords=keywords,
            brand=brand,
            count_only=is_counting,
            credentials=request.credentials.dict()
        )
        
        # Step 3: Format the response based on the task.
        if is_counting:
            count = result.get("total_count", 0)
            return ChatResponse(response_text=f"I found a total of **{count}** products matching your criteria.")
        else:
            products = result.get("items", [])
            total_count = result.get("total_count", 0)
            if not products:
                return ChatResponse(response_text=f"I couldn't find any products matching your search.")
            
            response_text = f"Here are the top {len(products)} of {total_count} results:"
            return ChatResponse(response_text=response_text, intent="search_products_result", data=products)

    except Exception as e:
        return ChatResponse(response_text=f"An error occurred: {e}")