from typing import Optional
from ..models.database import Product
from .supabase_client import SupabaseService


class ProductService:
    def __init__(self):
        self.supabase = SupabaseService()

    async def get_product_price(self, product_name: str) -> str:
        """
        Tool untuk mencari harga suatu produk.
        """
        product = await self.supabase.get_product_by_name(product_name)

        if product:
            unit_text = f" per {product.unit}" if product.unit else ""
            return f"Harga {product.name} (ID: {product.id}) saat ini adalah {product.price:,} {unit_text}."
        else:
            return f"Produk '{product_name}' tidak ditemukan di database."

    async def update_product_price(self, product_name: str, new_price: int, unit: Optional[str] = None, user_id: Optional[str] = None) -> str:
        """
        Tool untuk memperbarui harga produk yang sudah ada atau membuat produk baru jika belum ada.
        """
        try:
            # Validate price
            if new_price <= 0:
                return "Harga harus lebih dari 0."

            product = await self.supabase.upsert_product(
                product_name=product_name,
                price=new_price,
                unit=unit,
                user_id=user_id
            )

            unit_text = f" per {product.unit}" if product.unit else ""
            return f"Harga {product.name} (ID: {product.id}) berhasil diperbarui menjadi {new_price:,} {unit_text}."

        except Exception as e:
            return f"Terjadi kesalahan saat memperbarui produk: {str(e)}"

    async def delete_product(self, product_name: str, user_id: Optional[str] = None) -> str:
        """
        Tool untuk menghapus produk dari database.
        """
        try:
            success = await self.supabase.delete_product(
                product_name=product_name,
                user_id=user_id
            )

            if success:
                return f"Produk '{product_name}' berhasil dihapus dari database."
            else:
                return f"Produk '{product_name}' tidak ditemukan di database."

        except Exception as e:
            return f"Terjadi kesalahan saat menghapus produk: {str(e)}"

    async def update_product_by_id(self, product_id: int, new_price: int, unit: Optional[str] = None, user_id: Optional[str] = None) -> str:
        """
        Tool untuk memperbarui harga produk berdasarkan ID.
        """
        try:
            # Validate price
            if new_price <= 0:
                return "Harga harus lebih dari 0."

            product = await self.supabase.update_product_by_id(
                product_id=product_id,
                price=new_price,
                unit=unit,
                user_id=user_id
            )

            if product:
                unit_text = f" per {product.unit}" if product.unit else ""
                return f"Harga {product.name} (ID: {product.id}) berhasil diperbarui menjadi {new_price:,} {unit_text}."
            else:
                return f"Produk dengan ID {product_id} tidak ditemukan."

        except Exception as e:
            return f"Terjadi kesalahan saat memperbarui produk: {str(e)}"

    async def search_products(self, query: str) -> str:
        """
        Tool untuk mencari produk berdasarkan query.
        """
        try:
            products = await self.supabase.search_products(query)

            if not products:
                return f"Tidak ada produk yang ditemukan untuk query '{query}'."

            response_text = f"Ditemukan {len(products)} produk:\n\n"
            for product in products:
                unit_text = f" per {product.unit}" if product.unit else ""
                response_text += f"• {product.name} (ID: {product.id}): {product.price:,} {unit_text}\n"

            return response_text

        except Exception as e:
            return f"Terjadi kesalahan saat mencari produk: {str(e)}"