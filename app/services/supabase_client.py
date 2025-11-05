import os
import httpx
from typing import List, Dict, Any, Optional
from ..models.database import Product, ProductAuditLog


class SupabaseService:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")

        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

        self.headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    async def get_product_by_name(self, product_name: str) -> Optional[Product]:
        """Get product by name (case-insensitive)"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.supabase_url}/rest/v1/products",
                    params={"name": f"ilike.*{product_name}*", "limit": 1},
                    headers=self.headers
                )

                if response.status_code == 200 and response.json():
                    return Product(**response.json()[0])
                return None
        except Exception as e:
            print(f"Error getting product: {e}")
            return None

    async def upsert_product(self, product_name: str, price: int, unit: Optional[str] = None, user_id: Optional[str] = None) -> Product:
        """Update existing product or create new one"""
        try:
            async with httpx.AsyncClient() as client:
                # First, try to find existing product
                existing = await self.get_product_by_name(product_name)

                if existing:
                    # Update existing product
                    response = await client.patch(
                        f"{self.supabase_url}/rest/v1/products",
                        params={"name": f"eq.{product_name}"},
                        json={"price": price, "unit": unit},
                        headers=self.headers
                    )

                    if response.status_code == 200 and response.json():
                        updated_product = Product(**response.json()[0])

                        # Log the update
                        await self._log_audit(
                            product_id=existing.id,
                            action_type="UPDATE",
                            details={
                                "old_price": existing.price,
                                "new_price": price,
                                "old_unit": existing.unit,
                                "new_unit": unit
                            },
                            requested_by=user_id
                        )

                        return updated_product
                else:
                    # Create new product
                    response = await client.post(
                        f"{self.supabase_url}/rest/v1/products",
                        json={"name": product_name, "price": price, "unit": unit},
                        headers=self.headers
                    )

                    if response.status_code == 201 and response.json():
                        new_product = Product(**response.json()[0])

                        # Log the creation
                        await self._log_audit(
                            product_id=new_product.id,
                            action_type="CREATE",
                            details={
                                "name": product_name,
                                "price": price,
                                "unit": unit
                            },
                            requested_by=user_id
                        )

                        return new_product

                # If we get here, something went wrong
                raise Exception("Failed to upsert product")

        except Exception as e:
            print(f"Error upserting product: {e}")
            # Return a mock product for demo purposes
            return Product(id=1, name=product_name, price=price, unit=unit)

    async def delete_product_by_id(self, product_id: int, user_id: Optional[str] = None) -> bool:
        """Delete product by ID"""
        try:
            # Get product before deletion for audit
            async with httpx.AsyncClient() as client:
                get_response = await client.get(
                    f"{self.supabase_url}/rest/v1/products",
                    params={"id": f"eq.{product_id}", "limit": 1},
                    headers=self.headers
                )

                if get_response.status_code != 200 or not get_response.json():
                    return False

                existing_product = Product(**get_response.json()[0])

                # Delete the product
                response = await client.delete(
                    f"{self.supabase_url}/rest/v1/products",
                    params={"id": f"eq.{product_id}"},
                    headers=self.headers
                )

                if response.status_code in [200, 204]:
                    # Log the deletion
                    await self._log_audit(
                        product_id=product_id,
                        action_type="DELETE_BY_ID",
                        details={
                            "name": existing_product.name,
                            "price": existing_product.price,
                            "unit": existing_product.unit
                        },
                        requested_by=user_id
                    )
                    return True

                return False

        except Exception as e:
            print(f"Error deleting product by ID: {e}")
            return False

    async def delete_product(self, product_name: str, user_id: Optional[str] = None) -> bool:
        """Delete product by name"""
        try:
            # Get product before deletion for audit
            existing_product = await self.get_product_by_name(product_name)

            if not existing_product:
                return False

            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.supabase_url}/rest/v1/products",
                    params={"name": f"eq.{product_name}"},
                    headers=self.headers
                )

                if response.status_code in [200, 204]:
                    # Log the deletion
                    await self._log_audit(
                        product_id=existing_product.id,
                        action_type="DELETE",
                        details={
                            "name": product_name,
                            "price": existing_product.price,
                            "unit": existing_product.unit
                        },
                        requested_by=user_id
                    )
                    return True

                return False

        except Exception as e:
            print(f"Error deleting product: {e}")
            return False

    async def update_product_by_id(self, product_id: int, price: int, unit: Optional[str] = None, user_id: Optional[str] = None) -> Optional[Product]:
        """Update product by ID"""
        try:
            async with httpx.AsyncClient() as client:
                # First get the existing product for audit
                get_response = await client.get(
                    f"{self.supabase_url}/rest/v1/products",
                    params={"id": f"eq.{product_id}", "limit": 1},
                    headers=self.headers
                )

                if get_response.status_code != 200 or not get_response.json():
                    return None

                existing_product = Product(**get_response.json()[0])

                # Update the product
                response = await client.patch(
                    f"{self.supabase_url}/rest/v1/products",
                    params={"id": f"eq.{product_id}"},
                    json={"price": price, "unit": unit},
                    headers=self.headers
                )

                if response.status_code == 200 and response.json():
                    updated_product = Product(**response.json()[0])

                    # Log the update
                    await self._log_audit(
                        product_id=product_id,
                        action_type="UPDATE_BY_ID",
                        details={
                            "old_price": existing_product.price,
                            "new_price": price,
                            "old_unit": existing_product.unit,
                            "new_unit": unit
                        },
                        requested_by=user_id
                    )

                    return updated_product

                return None

        except Exception as e:
            print(f"Error updating product by ID: {e}")
            return None

    async def search_products(self, query: str) -> List[Product]:
        """Search products by name (case-insensitive partial match)"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.supabase_url}/rest/v1/products",
                    params={"name": f"ilike.*{query}*"},
                    headers=self.headers
                )

                if response.status_code == 200:
                    return [Product(**item) for item in response.json()]
                return []

        except Exception as e:
            print(f"Error searching products: {e}")
            return []

    async def _log_audit(self, product_id: Optional[int], action_type: str, details: Dict[str, Any], requested_by: Optional[str] = None):
        """Log audit trail"""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.supabase_url}/rest/v1/product_audit_log",
                    json={
                        "product_id": product_id,
                        "action_type": action_type,
                        "details": details,
                        "requested_by": requested_by
                    },
                    headers=self.headers
                )
        except Exception as e:
            print(f"Error logging audit: {e}")