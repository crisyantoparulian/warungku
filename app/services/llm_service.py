import os
import re
import json
from typing import Optional
from openai import OpenAI
from .product_service import ProductService


class LLMService:
    def __init__(self):
        self.product_service = ProductService()
        self.client = self._initialize_client()

    def _initialize_client(self):
        """Initialize OpenAI-compatible client for GLM"""
        api_key = os.getenv("GLM_API_KEY")
        base_url = os.getenv("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")

        if not api_key:
            raise ValueError("GLM_API_KEY must be set in environment variables")

        return OpenAI(
            api_key=api_key,
            base_url=base_url
        )

    async def process_message(self, message: str, user_id: Optional[str] = None) -> str:
        """
        Process user message and return appropriate response
        """
        try:
            # First try to use LLM for interpretation
            response = await self._interpret_with_llm(message, user_id)
            if response:
                return response

            # Fallback to manual interpretation
            return await self._fallback_interpretation(message, user_id)

        except Exception as e:
            print(f"Error in process_message: {e}")
            # Final fallback to manual interpretation
            return await self._fallback_interpretation(message, user_id)

    async def _interpret_with_llm(self, message: str, user_id: Optional[str] = None) -> Optional[str]:
        """
        Use LLM to interpret the message and determine the action
        """
        try:
            system_prompt = """Anda adalah asisten toko yang membantu mengelola produk. Tugas Anda adalah memahami permintaan pengguna dalam Bahasa Indonesia dan mengubahnya menjadi JSON format dengan struktur berikut:

Untuk mencari harga produk:
{
    "action": "get_price",
    "product_name": "nama_produk"
}

Untuk mengubah harga atau menambah produk:
{
    "action": "update_price",
    "product_name": "nama_produk",
    "price": 4000,
    "unit": "kg" (opsional)
}

Untuk mengubah harga berdasarkan ID:
{
    "action": "update_price_by_id",
    "product_id": 123,
    "price": 4000,
    "unit": "kg" (opsional)
}

Untuk menghapus produk:
{
    "action": "delete_product",
    "product_name": "nama_produk"
}

Untuk mencari produk:
{
    "action": "search_products",
    "query": "query_pencarian"
}

Hanya balas dengan JSON valid, tanpa penjelasan tambahan.

Contoh:
- "berapa harga minyak" -> {"action": "get_price", "product_name": "minyak"}
- "ubah harga minyak 4000" -> {"action": "update_price", "product_name": "minyak", "price": 4000}
- "update id 123 harga 4000" -> {"action": "update_price_by_id", "product_id": 123, "price": 4000}
- "ubah id 45 harga 5000 per kg" -> {"action": "update_price_by_id", "product_id": 45, "price": 5000, "unit": "kg"}
- "tambah gula 17000 per kg" -> {"action": "update_price", "product_name": "gula", "price": 17000, "unit": "kg"}
- "hapus produk beras" -> {"action": "delete_product", "product_name": "beras"}
- "cari produk minyak" -> {"action": "search_products", "query": "minyak"}"""

            response = self.client.chat.completions.create(
                model="glm-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                temperature=0.1,
                max_tokens=150
            )

            llm_response = response.choices[0].message.content.strip()

            # Try to parse JSON
            try:
                action_data = json.loads(llm_response)
                return await self._execute_action(action_data, user_id)
            except json.JSONDecodeError:
                print(f"Invalid JSON from LLM: {llm_response}")
                return None

        except Exception as e:
            print(f"Error in LLM interpretation: {e}")
            return None

    async def _execute_action(self, action_data: dict, user_id: Optional[str] = None) -> str:
        """
        Execute the action determined by the LLM
        """
        action = action_data.get("action")

        if action == "get_price":
            product_name = action_data.get("product_name", "")
            return await self.product_service.get_product_price(product_name)

        elif action == "update_price":
            product_name = action_data.get("product_name", "")
            price = action_data.get("price", 0)
            unit = action_data.get("unit")
            return await self.product_service.update_product_price(product_name, price, unit, user_id)

        elif action == "update_price_by_id":
            product_id = action_data.get("product_id", 0)
            price = action_data.get("price", 0)
            unit = action_data.get("unit")
            return await self.product_service.update_product_by_id(product_id, price, unit, user_id)

        elif action == "delete_product":
            product_name = action_data.get("product_name", "")
            return await self.product_service.delete_product(product_name, user_id)

        elif action == "search_products":
            query = action_data.get("query", "")
            return await self.product_service.search_products(query)

        else:
            return "Aksi tidak dikenali."

    async def _fallback_interpretation(self, message: str, user_id: Optional[str] = None) -> str:
        """
        Fallback method to interpret messages without LLM
        """
        message_lower = message.lower().strip()

        # Check for price queries
        if any(keyword in message_lower for keyword in ["berapa harga", "harga", "cari harga"]):
            # Extract product name
            for keyword in ["berapa harga", "harga", "cari harga"]:
                if keyword in message_lower:
                    product_name = message_lower.replace(keyword, "").strip()
                    if product_name:
                        return await self.product_service.get_product_price(product_name)

        # Check for update/create queries
        elif any(keyword in message_lower for keyword in ["ubah harga", "update harga", "ganti harga", "tambah", "tambahkan"]):
            # Try to extract price and product name
            price_match = re.search(r'\b(\d+)\b', message)
            if price_match:
                price = int(price_match.group(1))

                # Extract product name (remove price and keywords)
                for keyword in ["ubah harga", "update harga", "ganti harga", "tambah", "tambahkan"]:
                    if keyword in message_lower:
                        remaining = message_lower.replace(keyword, "").replace(str(price), "").strip()
                        # Extract unit if present
                        unit_match = re.search(r'per (\w+)$', remaining)
                        if unit_match:
                            unit = unit_match.group(1)
                            product_name = remaining.replace(f"per {unit}", "").strip()
                        else:
                            unit = None
                            product_name = remaining.strip()

                        if product_name:
                            return await self.product_service.update_product_price(product_name, price, unit, user_id)

        # Check for delete queries
        elif any(keyword in message_lower for keyword in ["hapus", "delete", "buang"]):
            for keyword in ["hapus", "delete", "buang"]:
                if keyword in message_lower:
                    product_name = message_lower.replace(keyword, "").strip()
                    if product_name:
                        return await self.product_service.delete_product(product_name, user_id)

        # Check for search queries
        elif any(keyword in message_lower for keyword in ["cari", "search", "tampilkan"]):
            for keyword in ["cari", "search", "tampilkan"]:
                if keyword in message_lower:
                    query = message_lower.replace(keyword, "").strip()
                    if query:
                        return await self.product_service.search_products(query)

        # Check for ID-based update queries
        elif any(keyword in message_lower for keyword in ["id", "update id", "ubah id"]):
            # Try to extract ID and price
            id_match = re.search(r'id\s*(\d+)', message_lower)
            price_match = re.search(r'\b(\d+)\b', message)

            if id_match and price_match:
                product_id = int(id_match.group(1))
                price = int(price_match.group(1))

                # Extract unit if present
                unit_match = re.search(r'per (\w+)$', message_lower)
                if unit_match:
                    unit = unit_match.group(1)
                else:
                    unit = None

                return await self.product_service.update_product_by_id(product_id, price, unit, user_id)

        # Default response
        return "Maaf, saya tidak mengerti permintaan Anda. Silakan coba dengan format seperti:\n\n• 'berapa harga minyak'\n• 'ubah harga minyak 4000'\n• 'update id 123 harga 4000'\n• 'ubah id 45 harga 5000 per kg'\n• 'tambah gula 17000 per kg'\n• 'hapus produk beras'\n• 'cari produk minyak'\n\n• Semua produk sekarang menampilkan ID untuk memudahkan update"