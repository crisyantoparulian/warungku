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

1. Untuk mencari produk:
{
    "action": "search_products",
    "query": "nama_produk"
}

2. Untuk mengubah harga berdasarkan ID:
{
    "action": "update_price_by_id",
    "product_id": 123,
    "price": 18000,
    "unit": "bks" (opsional)
}

3. Untuk menambah produk baru:
{
    "action": "update_price",
    "product_name": "nama_produk",
    "price": 17000,
    "unit": "bks" (opsional)
}

4. Untuk menghapus produk berdasarkan ID:
{
    "action": "delete_product_by_id",
    "product_id": 123
}

Hanya balas dengan JSON valid, tanpa penjelasan tambahan.

Contoh:
- "cari indomie" -> {"action": "search_products", "query": "indomie"}
- "ubah 5 18000 per bks" -> {"action": "update_price_by_id", "product_id": 5, "price": 18000, "unit": "bks"}
- "ubah 123 25000" -> {"action": "update_price_by_id", "product_id": 123, "price": 25000}
- "tambah gula 17000 per kg" -> {"action": "update_price", "product_name": "gula", "price": 17000, "unit": "kg"}
- "tambah kopi 15000" -> {"action": "update_price", "product_name": "kopi", "price": 15000}
- "hapus 5" -> {"action": "delete_product_by_id", "product_id": 5}

PENTING:
- Perintah "cari" untuk mencari produk
- Perintah "ubah" diikuti ID untuk update harga
- Perintah "tambah" untuk menambah produk baru
- Perintah "hapus" diikuti ID untuk menghapus produk"""

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
            print(f"🤖 LLM Response: {llm_response}")

            # Try to parse JSON
            try:
                action_data = json.loads(llm_response)
                print(f"📋 Parsed Action: {action_data}")
                result = await self._execute_action(action_data, user_id)
                print(f"✅ Final Result: {result}")
                return result
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON from LLM: {llm_response}")
                print(f"🔍 JSON Error: {e}")
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

        elif action == "delete_product_by_id":
            product_id = action_data.get("product_id", 0)
            return await self.product_service.delete_product_by_id(product_id, user_id)

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
        Following exact command patterns:
        1. cari {product name}
        2. ubah {id} {price} per {unit}
        3. tambah {product name} {price} per {unit}
        4. hapus {id}
        """
        message_lower = message.lower().strip()

        # Command 1: cari {product name}
        if message_lower.startswith("cari "):
            query = message_lower[5:].strip()
            if query:
                print(f"🔍 Search command detected: {query}")
                return await self.product_service.search_products(query)

        # Command 2: ubah {id} {price} per {unit}
        elif message_lower.startswith("ubah "):
            # Try to match: ubah {id} {price} per {unit}
            id_price_pattern = r'ubah\s+(\d+)\s+(\d+)'
            match = re.search(id_price_pattern, message_lower)

            if match:
                product_id = int(match.group(1))
                price = int(match.group(2))

                # Extract unit if present
                unit_match = re.search(r'per\s+(\w+)$', message_lower)
                unit = unit_match.group(1) if unit_match else None

                print(f"🎯 Update command detected: ID={product_id}, Price={price}, Unit={unit}")
                return await self.product_service.update_product_by_id(product_id, price, unit, user_id)

        # Command 3: tambah {product name} {price} per {unit}
        elif message_lower.startswith("tambah "):
            # Try to extract price and product name
            price_match = re.search(r'\b(\d+)\b', message)
            if price_match:
                price = int(price_match.group(1))
                remaining = message_lower[7:].replace(str(price), "").strip()

                # Extract unit if present
                unit_match = re.search(r'per\s+(\w+)$', remaining)
                if unit_match:
                    unit = unit_match.group(1)
                    product_name = remaining.replace(f"per {unit}", "").strip()
                else:
                    unit = None
                    product_name = remaining.strip()

                if product_name:
                    print(f"➕ Add command detected: Name={product_name}, Price={price}, Unit={unit}")
                    return await self.product_service.update_product_price(product_name, price, unit, user_id)

        # Command 4: hapus {id}
        elif message_lower.startswith("hapus "):
            id_part = message_lower[6:].strip()
            if id_part.isdigit():
                product_id = int(id_part)
                print(f"🗑️ Delete command detected: ID={product_id}")
                return await self.product_service.delete_product_by_id(product_id, user_id)

        # Default response
        print(f"🔄 Using fallback interpretation for: {message_lower}")
        print(f"⚠️  LLM failed to process the message correctly")
        return "Maaf, saya tidak mengerti permintaan Anda. Silakan coba dengan format seperti:\n\n• 'cari indomie'\n• 'ubah 5 18000 per bks'\n• 'ubah 123 25000'\n• 'tambah gula 17000 per kg'\n• 'tambah kopi 15000'\n• 'hapus 5'\n\n• Gunakan format: cari/ubah/tambah/hapus"