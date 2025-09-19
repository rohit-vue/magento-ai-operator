# backend/app/api/v1/endpoints/auth.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests
from requests_oauthlib import OAuth1 # We are going back to this library

router = APIRouter()

class ConnectionRequest(BaseModel):
    store_url: str
    consumer_key: str
    consumer_secret: str
    access_token: str
    access_token_secret: str

@router.post("/connect")
# This is now a standard function, not async
def test_magento_connection(request: ConnectionRequest):
    """
    Performs a simple, reliable, synchronous connection test that mimics Postman.
    """
    base_url = request.store_url.rstrip('/')
    # Use the proven index.php URL structure
    test_endpoint = f"{base_url}/index.php/rest/V1/products?searchCriteria[pageSize]=1"

    try:
        # This is the exact authentication method Postman uses.
        auth = OAuth1(
            client_key=request.consumer_key,
            client_secret=request.consumer_secret,
            resource_owner_key=request.access_token,
            resource_owner_secret=request.access_token_secret,
            signature_method='HMAC-SHA256'
        )

        # Make a direct, simple request.
        response = requests.get(test_endpoint, auth=auth, headers={'Content-Type': 'application/json'})
        response.raise_for_status() # This will raise an error for 4xx/5xx responses

        # If the product test succeeds, we can get the store name
        store_info_endpoint = f"{base_url}/index.php/rest/V1/store/storeViews"
        store_response = requests.get(store_info_endpoint, auth=auth)
        store_response.raise_for_status()
        store_data = store_response.json()
        
        first_store_name = store_data[0].get("name", "Unknown Store") if store_data else "Unknown Store"

        return {
            "status": "success",
            "message": f"Successfully connected to Magento store: '{first_store_name}'",
            "store_name": first_store_name
        }

    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        if status_code == 401:
            raise HTTPException(status_code=401, detail="Unauthorized: Invalid credentials or insufficient permissions. Please double-check every key and ensure the Integration has 'All' permissions and has been re-authorized.")
        else:
            raise HTTPException(status_code=status_code, detail=f"Magento API error: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")