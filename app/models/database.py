from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class Product(BaseModel):
    id: Optional[int] = None
    name: str
    price: int
    unit: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ProductAuditLog(BaseModel):
    id: Optional[int] = None
    product_id: Optional[int] = None
    action_type: str
    details: Optional[Dict[str, Any]] = None
    requested_by: Optional[str] = None
    timestamp: Optional[datetime] = None


class TelegramMessage(BaseModel):
    message_id: int
    from_id: int
    chat_id: int
    text: str
    date: datetime