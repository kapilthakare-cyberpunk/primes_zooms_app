
import os
from groq import Groq
from duckduckgo_search import DDGS

class AIAgent:
    def __init__(self, groq_api_key):
        self.client = Groq(api_key=groq_api_key)

    def _groq_chat_completion(self, messages, model="llama-3.3-70b-versatile", temperature=0.7):
        try:
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=model,
                temperature=temperature,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            return f"Error communicating with Groq API: {e}"

    def _duckduckgo_search(self, query):
        try:
            ddgs = DDGS()
            results = ddgs.text(keywords=query, max_results=3)
            return "\n".join([f"Title: {r["title"]}\nSnippet: {r["snippet"]}\nURL: {r["href"]}\n" for r in results])
        except Exception as e:
            return f"Error performing DuckDuckGo search: {e}"

class RentalConsultant(AIAgent):
    def __init__(self, groq_api_key, inventory_df):
        super().__init__(groq_api_key)
        self.inventory_df = inventory_df

    def consult(self, user_query):
        from csv_processor import search_items, get_item_details

        inventory_results = search_items(self.inventory_df, user_query)
        inventory_info = "INVENTORY (source of truth - ONLY suggest these items):\n"
        if inventory_results:
            for item in inventory_results:
                inventory_info += f"- {item.get("Item_Name")} (SKU: {item.get("SKU")}, Type: {item.get("Type")}, Status: {item.get("Status")})\n"
                inventory_info += f"  Rental Rates: 1 Day: ₹{item.get("1_Day")}, 2-4 Days: ₹{item.get("2-4_Days")}, 5-8 Days: ₹{item.get("5-8_Days")}, 9+ Days: ₹{item.get("9+_Days")}\n"
        else:
            inventory_info += "No matches found in inventory.\n"

        # Also include full inventory for context so the AI knows what exists
        full_inventory = "\nFULL INVENTORY LIST:\n"
        for _, row in self.inventory_df.iterrows():
            full_inventory += f"- {row.get("Item_Name")} | SKU: {row.get("SKU")} | Type: {row.get("Type")} | 1 Day: ₹{row.get("1_Day")} | Status: {row.get("Status")}\n"

        web_search_query = f"What is {user_query} used for? reviews and specs"
        web_info = self._duckduckgo_search(web_search_query)

        messages = [
            {"role": "system", "content": f"""You are a rental consultant for Primes & Zooms, a photo and cine gear rental service in Pune, India.

CRITICAL RULES:
1. ONLY suggest items that exist in the INVENTORY below. NEVER invent, assume, or hallucinate items not listed.
2. If the user asks about something not in the inventory, say "We don't currently have that in our rental inventory" and suggest the closest alternatives FROM the inventory.
3. All pricing must come from the inventory data. NEVER make up prices.
4. For policies, FAQ, rental terms, deposit info, or questions you cannot answer from inventory data, tell the user to check the official website at https://primesandzooms.com or suggest they use the Page Agent copilot in the sidebar to visit the site directly.
5. Always mention actual rental rates from the inventory when recommending items.

{inventory_info}
{full_inventory}

Web search results (for product specs/info only, NOT for pricing): {web_info}"""},
            {"role": "user", "content": user_query}
        ]
        return self._groq_chat_completion(messages)

class PricingAssistant(AIAgent):
    def __init__(self, groq_api_key, inventory_df):
        super().__init__(groq_api_key)
        self.inventory_df = inventory_df

    def suggest_pricing(self, item_name, current_mrp=None, category=None):
        from csv_processor import search_items

        similar_items_info = "SIMILAR ITEMS IN INVENTORY (source of truth):\n"
        if category:
            similar_items = self.inventory_df[self.inventory_df["Type"].str.contains(category, case=False, na=False)]
            if not similar_items.empty:
                for _, item in similar_items.iterrows():
                    similar_items_info += f"- {item.get("Item_Name")} | MRP: ₹{item.get("MRP")} | 1 Day: ₹{item.get("1_Day")} | 2-4 Days: ₹{item.get("2-4_Days")} | 5-8 Days: ₹{item.get("5-8_Days")} | 9+ Days: ₹{item.get("9+_Days")}\n"

        # Full inventory for pricing context
        full_inventory = "\nFULL INVENTORY WITH ALL RATES:\n"
        for _, row in self.inventory_df.iterrows():
            full_inventory += f"- {row.get("Item_Name")} | Type: {row.get("Type")} | MRP: ₹{row.get("MRP")} | 1D: ₹{row.get("1_Day")} | 2-4D: ₹{row.get("2-4_Days")} | 5-8D: ₹{row.get("5-8_Days")} | 9+D: ₹{row.get("9+_Days")}\n"

        web_search_query = f"{item_name} market rental price India"
        web_info = self._duckduckgo_search(web_search_query)

        messages = [
            {"role": "system", "content": f"""You are a pricing assistant for Primes & Zooms, a photo and cine gear rental service in Pune, India.

CRITICAL RULES:
1. ONLY analyze and suggest pricing for items that exist in the INVENTORY below. NEVER invent items.
2. All base pricing data must come from the inventory. Use web search ONLY for market context, not as pricing source.
3. Suggest rental slab rates (1 Day, 2-4 Days, 5-8 Days, 9+ Days) that are consistent with the existing pricing patterns in the inventory.
4. Typical discount pattern: 2-4 days = ~85% of 1-day rate, 5-8 days = ~75%, 9+ days = ~65%. Adjust based on item type.
5. For policies, deposit structures, or terms you cannot answer from inventory data, direct users to https://primesandzooms.com or suggest using the Page Agent copilot sidebar tool.

{similar_items_info}
{full_inventory}

Web search results (market context only): {web_info}"""},
            {"role": "user", "content": f"Suggest pricing for: {item_name}"}
        ]
        return self._groq_chat_completion(messages)
