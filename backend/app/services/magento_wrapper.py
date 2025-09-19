# backend/app/services/magento_wrapper.py
import requests
import urllib.parse
from requests_oauthlib import OAuth1

class MagentoService:
    def _make_request(self, method: str, endpoint: str, credentials: dict, query_params: str = ""):
        # This is the only internal helper. It is proven to work.
        if not credentials: raise ValueError("Magento credentials are required.")
        base_url = credentials['store_url'].rstrip('/')
        full_request_url = f"{base_url}/index.php/rest/V1{endpoint}{query_params}"
        auth = OAuth1(client_key=credentials['consumer_key'], client_secret=credentials['consumer_secret'], resource_owner_key=credentials['access_token'], resource_owner_secret=credentials['access_token_secret'], signature_method='HMAC-SHA256')
        try:
            response = requests.request(method, full_request_url, auth=auth, headers={'Content-Type': 'application/json'})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_message = e.response.json().get("message", e.response.reason) if e.response.text else e.response.reason
            raise Exception(f"Magento API Error: {e.response.status_code} - {error_message}")

    def product_search(self, keywords: str = None, brand: str = None, filters: list = None, count_only: bool = False, limit: int = 10, credentials: dict = None) -> dict:
        print(f"ULTRA-ROBUST SEARCH: keywords='{keywords}', brand='{brand}', filters={filters}")
        
        endpoint = "/products"
        filter_groups = []
        
        # --- All logic is now self-contained and safe ---

        # Handle Brand
        if brand:
            brand_id = None
            try:
                brand_options_endpoint = "/products/attributes/manufacturer/options"
                options = self._make_request("GET", brand_options_endpoint, credentials)
                if isinstance(options, list):
                    for option in options:
                        if isinstance(option, dict) and option.get('label', '').strip().lower() == brand.strip().lower():
                            brand_id = option.get('value')
                            break
            except Exception as e:
                print(f"INFO: Could not get brand options, will fall back to text search. Error: {e}")
            
            if brand_id:
                filter_groups.append(f"&searchCriteria[filter_groups][{len(filter_groups)}][filters][0][field]=manufacturer&searchCriteria[filter_groups][{len(filter_groups)}][filters][0][value]={brand_id}&searchCriteria[filter_groups][{len(filter_groups)}][filters][0][condition_type]=eq")
            else:
                encoded_brand = urllib.parse.quote(f'%{brand}%')
                filter_groups.append(f"&searchCriteria[filter_groups][{len(filter_groups)}][filters][0][field]=manufacturer&searchCriteria[filter_groups][{len(filter_groups)}][filters][0][value]={encoded_brand}&searchCriteria[filter_groups][{len(filter_groups)}][filters][0][condition_type]=like")
        
        # Handle Special Filters from AI (like 'on_sale')
        if isinstance(filters, list):
            for f in filters:
                if isinstance(f, dict):
                    key = f.get("key", "").lower()
                    if key == 'on_sale' and f.get("value", "").lower() == 'true':
                        filter_groups.append(f"&searchCriteria[filter_groups][{len(filter_groups)}][filters][0][field]=special_price&searchCriteria[filter_groups][{len(filter_groups)}][filters][0][condition_type]=notnull")

        # Handle Keywords
        if keywords:
            encoded_kw = urllib.parse.quote(f'%{keywords}%')
            filter_groups.append(
                f"&searchCriteria[filter_groups][{len(filter_groups)}][filters][0][field]=name&searchCriteria[filter_groups][{len(filter_groups)}][filters][0][value]={encoded_kw}&searchCriteria[filter_groups][{len(filter_groups)}][filters][0][condition_type]=like"
                f"&searchCriteria[filter_groups][{len(filter_groups)}][filters][1][field]=sku&searchCriteria[filter_groups][{len(filter_groups)}][filters][1][value]={encoded_kw}&searchCriteria[filter_groups][{len(filter_groups)}][filters][1][condition_type]=like"
                f"&searchCriteria[filter_groups][{len(filter_groups)}][filters][2][field]=short_description&searchCriteria[filter_groups][{len(filter_groups)}][filters][2][value]={encoded_kw}&searchCriteria[filter_groups][{len(filter_groups)}][filters][2][condition_type]=like"
            )

        if not filter_groups: return {"items": [], "total_count": 0}

        query_string = "".join(filter_groups)
        fields_to_fetch = "total_count" if count_only else "items[id,sku,name,price,custom_attributes,media_gallery_entries[id,file,types]]"
        page_size = 0 if count_only else limit
        query_params = (f"?{query_string.lstrip('&')}" f"&searchCriteria[pageSize]={page_size}" f"&fields={fields_to_fetch}")
        
        raw_result = self._make_request("GET", endpoint, credentials, query_params=query_params)
        
        # Bulletproof parsing
        items = raw_result.get('items', []) if isinstance(raw_result, dict) else []
        total_count = raw_result.get('total_count', 0) if isinstance(raw_result, dict) else 0
            
        if count_only: 
            return {"total_count": total_count}

        # Format results
        formatted_products = []
        for product in items:
            if not isinstance(product, dict): continue
            
            # --- Formatting logic is now self-contained and safe ---
            
            # Description
            description = "No description available."
            custom_attrs = product.get('custom_attributes')
            if isinstance(custom_attrs, list):
                for attr in custom_attrs:
                    if isinstance(attr, dict) and attr.get('attribute_code') == 'short_description':
                        description = attr.get('value')
                        break
            
            # Image
            image_path = ""
            gallery = product.get('media_gallery_entries')
            if isinstance(gallery, list) and len(gallery) > 0:
                image_path = gallery[0].get('file', '')
            
            # Price
            price_val = product.get('price')
            display_price = f"${float(price_val):.2f}" if price_val is not None else "N/A"
            
            # Append
            formatted_products.append({ "id": product.get('id'), "sku": product.get('sku'), "name": product.get('name'), "price": display_price, "image_url": f"{credentials['store_url'].rstrip('/')}/media/catalog/product{image_path}" if image_path else "", "description": description })
            
        return {"items": formatted_products, "total_count": total_count}

magento_service = MagentoService()