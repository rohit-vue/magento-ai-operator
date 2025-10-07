# backend/app/services/magento_wrapper.py
import requests
import urllib.parse
import re
from requests_oauthlib import OAuth1

class MagentoService:
    def _make_request(self, method: str, endpoint: str, credentials: dict, query_params: str = ""):
        if not credentials: raise ValueError("Magento credentials are required.")
        base_url = credentials['store_url'].rstrip('/')
        full_request_url = f"{base_url}/index.php/rest/V1{endpoint}{query_params}"
        auth = OAuth1(client_key=credentials['consumer_key'], client_secret=credentials['consumer_secret'], resource_owner_key=credentials['access_token'], resource_owner_secret=credentials['access_token_secret'], signature_method='HMAC-SHA256')
        try:
            response = requests.request(method, full_request_url, auth=auth, headers={'Content-Type': 'application/json'})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_message = e.response.reason
            try: error_message = e.response.json().get("message", e.response.reason)
            except: pass
            raise Exception(f"Magento API Error: {e.response.status_code} - {error_message}")

    def _get_brand_id(self, brand_name: str, credentials: dict) -> str | None:
        attribute_code_for_brand = "manufacturer"
        endpoint = f"/products/attributes/{attribute_code_for_brand}/options"
        try:
            options = self._make_request("GET", endpoint, credentials)
            if isinstance(options, list):
                for option in options:
                    if isinstance(option, dict) and option.get('label', '').strip().lower() == brand_name.strip().lower():
                        return option.get('value')
            return None
        except Exception as e:
            print(f"INFO: Could not get brand options for '{brand_name}'. Error: {e}")
            return None

    def product_search(self, keywords: str = None, brand: str = None, count_only: bool = False, credentials: dict = None) -> dict:
        print(f"BRAND-AWARE SEARCH: keywords='{keywords}', brand='{brand}', count_only={count_only}")
        
        endpoint = "/products"
        filter_groups = []
        
        # --- THIS IS THE CORRECTED LOGIC ---

        # Part 1: Handle Brand (This MUST be a separate filter group for AND logic)
        if brand:
            brand_id = self._get_brand_id(brand, credentials)
            if brand_id:
                filter_groups.append(f"&searchCriteria[filter_groups][{len(filter_groups)}][filters][0][field]=manufacturer&searchCriteria[filter_groups][{len(filter_groups)}][filters][0][value]={brand_id}&searchCriteria[filter_groups][{len(filter_groups)}][filters][0][condition_type]=eq")
            else:
                # If brand was specified but no ID was found, the search must fail.
                print(f"Brand '{brand}' specified but no ID found. Returning 0 results.")
                return {"items": [], "total_count": 0}

        # Part 2: Handle Keywords (This is a separate filter group)
        if keywords:
            encoded_kw = urllib.parse.quote(f'%{keywords}%')
            # One group for OR condition between name, sku, and description
            filter_groups.append(
                f"&searchCriteria[filter_groups][{len(filter_groups)}][filters][0][field]=name&searchCriteria[filter_groups][{len(filter_groups)}][filters][0][value]={encoded_kw}&searchCriteria[filter_groups][{len(filter_groups)}][filters][0][condition_type]=like"
                f"&searchCriteria[filter_groups][{len(filter_groups)}][filters][1][field]=sku&searchCriteria[filter_groups][{len(filter_groups)}][filters][1][value]={encoded_kw}&searchCriteria[filter_groups][{len(filter_groups)}][filters][1][condition_type]=like"
                f"&searchCriteria[filter_groups][{len(filter_groups)}][filters][2][field]=short_description&searchCriteria[filter_groups][{len(filter_groups)}][filters][2][value]={encoded_kw}&searchCriteria[filter_groups][{len(filter_groups)}][filters][2][condition_type]=like"
            )

        if not filter_groups: return {"items": [], "total_count": 0}

        query_string = "".join(filter_groups)
        fields_to_fetch = "total_count" if count_only else "items[id,sku,name,price,custom_attributes,media_gallery_entries[id,file,types]]"
        page_size = 0 if count_only else 10
        query_params = (f"?{query_string.lstrip('&')}" f"&searchCriteria[pageSize]={page_size}" f"&fields={fields_to_fetch}")
        
        raw_result = self._make_request("GET", endpoint, credentials, query_params=query_params)
        
        items = raw_result.get('items', []) if isinstance(raw_result, dict) else []
        total_count = raw_result.get('total_count', 0) if isinstance(raw_result, dict) else 0
            
        if count_only: 
            return {"total_count": total_count}

        # Format results (bulletproof version)
        formatted_products = []
        for p in items:
            if not isinstance(p, dict): continue
            
            description_html = ""
            custom_attrs = p.get('custom_attributes', [])
            if isinstance(custom_attrs, list):
                description_html = next((attr.get('value', '') for attr in custom_attrs if isinstance(attr, dict) and attr.get('attribute_code') == 'short_description'), "")
            
            clean_description = re.sub('<[^<]+?>', '', description_html or "").strip()
            description = (clean_description[:100] + '...') if len(clean_description) > 100 else clean_description
            if not description: description = "No description available."

            image_path = ""
            gallery = p.get('media_gallery_entries', []) or []
            if isinstance(gallery, list) and gallery:
                img_path = next((e.get('file') for e in gallery if isinstance(e, dict) and 'image' in e.get('types', [])), None)
                if not img_path: img_path = gallery[0].get('file', '')
            
            price_val = p.get('price')
            display_price = f"${float(price_val):.2f}" if price_val is not None else "Price not available"
            
            formatted_products.append({ "id": p.get('id'), "sku": p.get('sku'), "name": p.get('name'), "price": display_price, "image_url": f"{credentials['store_url'].rstrip('/')}/media/catalog/product{img_path}" if img_path else "", "description": description })
            
        return {"items": formatted_products, "total_count": total_count}

magento_service = MagentoService()