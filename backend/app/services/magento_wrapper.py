# backend/app/services/magento_wrapper.py
import requests
import urllib.parse
from requests_oauthlib import OAuth1

class MagentoService:
    def _make_request(self, method: str, endpoint: str, credentials: dict, json_payload: dict = None, query_params: str = ""):
        if not credentials:
            raise ValueError("Magento credentials are required for API calls.")
        base_url = credentials['store_url'].rstrip('/')
        full_request_url = f"{base_url}/index.php/rest/V1{endpoint}{query_params}"
        auth = OAuth1(client_key=credentials['consumer_key'], client_secret=credentials['consumer_secret'], resource_owner_key=credentials['access_token'], resource_owner_secret=credentials['access_token_secret'], signature_method='HMAC-SHA256')
        try:
            response = requests.request(method, full_request_url, auth=auth, json=json_payload, headers={'Content-Type': 'application/json'})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"Magento API Error ({e.response.status_code}): {e.response.text}")
            raise Exception(f"Magento API Error: {e.response.status_code} - {e.response.text}")

    def _get_attribute_value(self, product, attribute_code):
        if 'custom_attributes' in product and isinstance(product['custom_attributes'], list):
            for attr in product['custom_attributes']:
                if isinstance(attr, dict) and attr.get('attribute_code') == attribute_code:
                    return attr.get('value')
        return None
    
    def _get_brand_id(self, brand_name: str, credentials: dict) -> str | None:
        print(f"Looking up Brand ID for: '{brand_name}' using 'manufacturer' attribute")
        attribute_code_for_brand = "manufacturer"
        endpoint = f"/products/attributes/{attribute_code_for_brand}/options"
        try:
            options = self._make_request("GET", endpoint, credentials)
            if not isinstance(options, list):
                if isinstance(options, dict) and options.get('label','').lower() == brand_name.lower():
                    return options.get('value')
                print(f"Warning: API response for '{attribute_code_for_brand}' options was not a list.")
                return None
            for option in options:
                if isinstance(option, dict) and option.get('label', '').lower() == brand_name.lower():
                    brand_id = option.get('value')
                    if brand_id:
                        print(f"Found Brand ID: {brand_id}")
                        return brand_id
            print(f"Could not find an ID for brand '{brand_name}'.")
            return None
        except Exception as e:
            print(f"Error finding brand ID: {e}")
            return None

    def search_products(self, search_params: dict, credentials: dict) -> list:
        print(f"FINAL Magento Search: Searching with params: {search_params}")
        
        endpoint = "/products"
        filter_groups = []

        def add_filter(field, value, condition='eq'):
            safe_field = urllib.parse.quote(field.lower().replace(' ', '_'))
            encoded_value = urllib.parse.quote(str(value))
            if condition == 'like':
                encoded_value = urllib.parse.quote(f'%{str(value)}%')
            
            filter_groups.append(
                f"&searchCriteria[filter_groups][{len(filter_groups)}][filters][0][field]={safe_field}"
                f"&searchCriteria[filter_groups][{len(filter_groups)}][filters][0][value]={encoded_value}"
                f"&searchCriteria[filter_groups][{len(filter_groups)}][filters][0][condition_type]={condition}"
            )

        if search_params.get("brand"):
            brand_id = self._get_brand_id(search_params["brand"], credentials)
            if brand_id:
                add_filter('manufacturer', brand_id, 'eq')
            else:
                return []

        if search_params.get("query"):
            query = search_params["query"]
            encoded_query = urllib.parse.quote(f'%{query}%')
            filter_groups.append(
                f"&searchCriteria[filter_groups][{len(filter_groups)}][filters][0][field]=name"
                f"&searchCriteria[filter_groups][{len(filter_groups)}][filters][0][value]={encoded_query}"
                f"&searchCriteria[filter_groups][{len(filter_groups)}][filters][0][condition_type]=like"
                f"&searchCriteria[filter_groups][{len(filter_groups)}][filters][1][field]=sku"
                f"&searchCriteria[filter_groups][{len(filter_groups)}][filters][1][value]={encoded_query}"
                f"&searchCriteria[filter_groups][{len(filter_groups)}][filters][1][condition_type]=like"
            )
        
        if search_params.get("attributes"):
            for attr in search_params.get("attributes", []):
                key = attr.get('key')
                value = attr.get('value')
                if key and value:
                    add_filter(key, value, 'like')

        if not filter_groups: return []

        query_string = "".join(filter_groups)
        query_params = (f"?{query_string.lstrip('&')}" f"&searchCriteria[pageSize]=10" f"&fields=items[id,sku,name,price,custom_attributes,media_gallery_entries[id,file,types]]")
        
        try:
            result = self._make_request("GET", endpoint, credentials, query_params=query_params)
        except Exception as e:
            print(f"Error during API call in search_products: {e}")
            return []

        formatted_products = []
        items = result.get('items', [])
        if not isinstance(items, list): items = []

        for product in items:
            if not isinstance(product, dict): continue

            # --- DIAGNOSTIC PRINT STATEMENT IS HERE ---
            print(f"RAW PRODUCT DATA for SKU {product.get('sku')}: {product}")

            image_path = ""
            try:
                gallery_entries = product.get('media_gallery_entries')
                if gallery_entries and isinstance(gallery_entries, list):
                    for entry in gallery_entries:
                        if not isinstance(entry, dict): continue
                        entry_types = entry.get('types', [])
                        if isinstance(entry_types, list) and ('image' in entry_types or 'base' in entry_types):
                            image_path = entry.get('file')
                            if image_path: break
                    if not image_path:
                        for entry in gallery_entries:
                            if isinstance(entry, dict):
                                image_path = entry.get('file')
                                if image_path: break
            except Exception as e: print(f"Error processing image for SKU {product.get('sku')}: {e}")
            
            description = "No description available."
            try:
                desc_short = self._get_attribute_value(product, 'short_description')
                desc_long = self._get_attribute_value(product, 'description')
                if desc_short and isinstance(desc_short, str): description = desc_short
                elif desc_long and isinstance(desc_long, str): description = desc_long
            except Exception as e: print(f"Error processing description for SKU {product.get('sku')}: {e}")
            
            try:
                # --- THIS IS THE NEW, SMARTER FORMATTING LOGIC ---
                
                # Handle Price Formatting
                price_value = product.get('price')
                if price_value is None or float(price_value) >= 99999.00:
                    display_price = "Contact for Price"
                else:
                    display_price = f"${float(price_value):.2f}"
                
                # Handle Image URL
                image_url = f"{credentials['store_url'].rstrip('/')}/media/catalog/product{image_path}" if image_path else ""
                
                formatted_products.append({ 
                    "id": product.get('id'), 
                    "sku": product.get('sku'), 
                    "name": product.get('name'), 
                    "price": display_price, # Use the new display_price variable
                    "image_url": image_url, 
                    "description": description, 
                })
            except (ValueError, TypeError) as e:
                 print(f"Error formatting price for SKU {product.get('sku')}, price value was '{product.get('price')}': {e}")
            except Exception as e:
                 print(f"Error formatting final product data for SKU {product.get('sku')}: {e}")
        
        return formatted_products

    def aggregate_products(self, agg_params: dict, credentials: dict) -> dict:
        # We keep the full function to avoid syntax errors
        print(f"AGGREGATE Magento: Performing aggregation with params: {agg_params}")
        if agg_params.get("aggregation_type") != "count": return {"error": "Unsupported aggregation type."}
        filter_by = agg_params.get("filter_by", {})
        query_params = ""
        filter_field = ""
        filter_value = ""
        if filter_by.get("category"):
            filter_field = "primary_category"
            filter_value = urllib.parse.quote(filter_by["category"])
        elif filter_by.get("attribute"):
            attr = filter_by.get("attribute", {})
            filter_field = urllib.parse.quote(attr.get('key', ''))
            filter_value = urllib.parse.quote(attr.get('value', ''))
        else: return {"error": "No valid filter provided for aggregation."}
        if not filter_field or not filter_value: return {"error": "Invalid filter provided for aggregation."}
        query_params = (f"?searchCriteria[filter_groups][0][filters][0][field]={filter_field}" f"&searchCriteria[filter_groups][0][filters][0][value]={filter_value}" f"&searchCriteria[filter_groups][0][filters][0][condition_type]=eq")
        endpoint = "/products"
        query_params += "&fields=total_count"
        try:
            result = self._make_request("GET", endpoint, credentials, query_params=query_params)
            count = result.get("total_count", 0)
            return {"count": count, "filter": filter_by}
        except Exception as e:
            print(f"Error during API call in aggregate_products: {e}")
            return {"error": str(e)}

magento_service = MagentoService()