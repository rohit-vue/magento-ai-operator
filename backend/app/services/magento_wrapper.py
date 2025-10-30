# backend/app/services/magento_wrapper.py
import requests
import urllib.parse
from requests_oauthlib import OAuth1
import re

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
            error_message = e.response.json().get("message", e.response.reason) if e.response.text else e.response.reason
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
            print(f"INFO: Could not get brand options for '{brand_name}', will fall back to text search. Error: {e}")
            return None

    def product_query(self, params: dict, credentials: dict) -> dict:
        print(f"UNIFIED QUERY with params: {params}")
        
        endpoint = "/products"
        query_parts = []
        filter_group_index = 0
        
        # --- THE FINAL STRATEGY: UNIFIED searchCriteria ---

        # Group 1: Keywords (Searches multiple fields with OR logic)
        # This now replicates your proven Postman blueprint for keyword search.
        search_string = params.get("sku") or params.get("keywords")
        if search_string:
            encoded_kw = urllib.parse.quote(search_string)
            fields_to_search = ["name", "sku", "short_description"]
            for i, field in enumerate(fields_to_search):
                query_parts.append(f"searchCriteria[filter_groups][{filter_group_index}][filters][{i}][field]={field}")
                query_parts.append(f"searchCriteria[filter_groups][{filter_group_index}][filters][{i}][value]=%{encoded_kw}%")
                query_parts.append(f"searchCriteria[filter_groups][{filter_group_index}][filters][{i}][condition_type]=like")
            filter_group_index += 1

        # Subsequent groups are for all other filters, combined with AND logic.
        if params.get("brand"):
            brand_id = self._get_brand_id(params["brand"], credentials)
            if brand_id:
                query_parts.append(f"searchCriteria[filter_groups][{filter_group_index}][filters][0][field]=manufacturer&searchCriteria[filter_groups][{filter_group_index}][filters][0][value]={brand_id}&searchCriteria[filter_groups][{filter_group_index}][filters][0][condition_type]=eq")
                filter_group_index += 1
            else:
                return {"items": [], "total_count": 0}

        if params.get("on_sale"):
            query_parts.append(f"searchCriteria[filter_groups][{filter_group_index}][filters][0][field]=special_price&searchCriteria[filter_groups][{filter_group_index}][filters][0][condition_type]=notnull")
            filter_group_index += 1
        
        # This attribute search is now more reliable within this structure
        if params.get("attributes"):
            attributes_to_filter = params["attributes"]
            if isinstance(attributes_to_filter, dict):
                for attr_code, attr_value in attributes_to_filter.items():
                    encoded_value = urllib.parse.quote(str(attr_value))
                    query_parts.append(f"searchCriteria[filter_groups][{filter_group_index}][filters][0][field]={attr_code}&searchCriteria[filter_groups][{filter_group_index}][filters][0][value]=%{encoded_value}%&searchCriteria[filter_groups][{filter_group_index}][filters][0][condition_type]=like")
                    filter_group_index += 1

        # --- Assemble the final query string ---
        task = params.get("task", "search")
        limit = params.get("limit", 10)
        
        if task == "count":
            query_parts.append("searchCriteria[pageSize]=0")
            query_parts.append("fields=total_count")
        else:
            query_parts.append(f"searchCriteria[pageSize]={limit}")
            query_parts.append("fields=items[id,sku,name,price,special_price,custom_attributes,media_gallery_entries[id,file,types]],total_count")

        query_string = "&".join(query_parts)
        query_params = f"?{query_string}"

        raw_result = self._make_request("GET", endpoint, credentials, query_params=query_params)
        
        # Data formatting part is correct and unchanged
        items = raw_result.get('items', []) if isinstance(raw_result, dict) else []
        if not isinstance(items, list): items = []
        total_count = raw_result.get('total_count', 0) if isinstance(raw_result, dict) else 0
            
        if task == "count": 
            return {"total_count": total_count}

        formatted_products = []
        for product in items:
            if not isinstance(product, dict): continue
            description = "No description available."
            description_html, short_description_html = "", ""
            custom_attrs = product.get('custom_attributes', [])
            if isinstance(custom_attrs, list):
                for attr in custom_attrs:
                    if not isinstance(attr, dict): continue
                    if attr.get('attribute_code') == 'short_description': short_description_html = attr.get('value', '')
                    if attr.get('attribute_code') == 'description': description_html = attr.get('value', '')
            final_html = short_description_html or description_html
            if final_html and isinstance(final_html, str):
                clean_desc = re.sub('<[^<]+?>', '', final_html); clean_desc = re.sub('&[a-zA-Z0-9]+;', ' ', clean_desc).strip()
                if clean_desc: description = clean_desc
            image_path = ""
            gallery = product.get('media_gallery_entries', [])
            if isinstance(gallery, list) and gallery:
                for entry in gallery:
                    if isinstance(entry, dict):
                        types = entry.get('types', [])
                        if isinstance(types, list) and 'image' in types: image_path = entry.get('file'); break
                if not image_path and gallery and isinstance(gallery[0], dict): image_path = gallery[0].get('file', '')
            display_price = "Price not available"
            try:
                special_price_val, price_val = product.get('special_price'), product.get('price')
                if special_price_val is not None and float(special_price_val) < float(price_val):
                    display_price = f"<del>${float(price_val):.2f}</del> <strong>${float(special_price_val):.2f}</strong>"
                elif price_val is not None:
                    display_price = f"${float(price_val):.2f}"
            except (ValueError, TypeError, AttributeError): pass
            formatted_products.append({"id": product.get('id'), "sku": product.get('sku'), "name": product.get('name'), "price": display_price, "image_url": f"{credentials['store_url'].rstrip('/')}/media/catalog/product{image_path}" if image_path else "", "description": description})
            
        return {"items": formatted_products, "total_count": total_count}

    def get_product_details_by_sku(self, sku: str, credentials: dict) -> dict | None:
        print(f"Getting full details for SKU: {sku}")
        try:
            safe_sku = urllib.parse.quote(sku, safe='')
            endpoint = f"/products/{safe_sku}"
            return self._make_request("GET", endpoint, credentials)
        except Exception as e:
            print(f"Error getting details for SKU {sku}: {e}")
            return None

magento_service = MagentoService()