# backend/app/api/v1/endpoints/chatbot.py
import json
from fastapi import APIRouter
from app.schemas.chatbot import ChatRequest, ChatResponse
from app.services.nlu_service import classify_intent, client as openai_client
from app.services.magento_wrapper import magento_service
from app.core.config import settings
import traceback

router = APIRouter()

@router.post("/chat")
async def handle_chat(request: ChatRequest):
    if not request.credentials:
        return ChatResponse(response_text="Please connect to a store first.")

    params = await classify_intent(request.message)
    task = params.get("task")

    if task == "details" and not params.get("question"):
        task = "search"

    if task == "error":
        return ChatResponse(response_text=f"Sorry, I had an issue understanding that. Details: {params.get('details')}")

    try:
        if task == "search" or task == "count":
            # --- THIS IS THE FIX ---
            # Remove the 'original_message' argument as it's no longer needed.
            result = magento_service.product_query(params, request.credentials.dict())
            # --- END OF FIX ---
            
            if task == "count":
                count = result.get("total_count", 0)
                summary_parts = []
                if params.get("brand"): summary_parts.append(f"for the brand '{params['brand']}'")
                if params.get("keywords"): summary_parts.append(f"matching '{params['keywords']}'")
                summary_text = " ".join(summary_parts)
                return ChatResponse(response_text=f"I found a total of **{count}** products {summary_text}.")
            else:
                products = result.get("items", [])
                total_count = result.get("total_count", 0)
                if not products:
                    return ChatResponse(response_text="I couldn't find any products matching your search.")
                response_text = f"Here are the top {len(products)} of {total_count} results:"
                return ChatResponse(response_text=response_text, intent="search_products_result", data=products)

        elif task == "details":
            # ... (rest of the file is correct and unchanged)
            sku = params.get("sku") or params.get("keywords")
            if not sku and request.context:
                context = request.context
                if isinstance(context, list) and context: sku = context[0].get('sku')
                elif isinstance(context, dict): sku = context.get('sku')
            question = params.get("question", request.message)
            if not sku: return ChatResponse(response_text="Please specify a product SKU to get details, or ask about a product I just found.")
            product_data = magento_service.get_product_details_by_sku(sku, request.credentials.dict())
            if not product_data: return ChatResponse(response_text=f"Sorry, I couldn't find data for SKU '{sku}'.")
            system_prompt = ("You are a friendly and knowledgeable e-commerce expert from Lumenco...")
            context_summary = {"name": product_data.get("name"), "sku": product_data.get("sku"), "price": product_data.get("price"), "attributes": { attr.get("attribute_code"): attr.get("value") for attr in product_data.get("custom_attributes", []) if isinstance(attr, dict) }}
            user_prompt = f"PRODUCT DATA:\n```json\n{json.dumps(context_summary, indent=2)}\n```\n\nUSER QUESTION:\n{question}"
            response = await openai_client.chat.completions.create(model=settings.LLM_MODEL_NAME, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], temperature=0.2)
            answer = response.choices[0].message.content
            return ChatResponse(response_text=answer, data=product_data)
        
        else:
            return ChatResponse(response_text="I'm not sure how to handle that task.")

    except Exception as e:
        print(f"An unexpected error occurred in the chat endpoint: {e}")
        traceback.print_exc()
        return ChatResponse(response_text=f"An error occurred. Please check the server logs for details.")