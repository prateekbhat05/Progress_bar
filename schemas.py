# app/schemas.py
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime

# Product schemas
class ProductBase(BaseModel):
    sku: str = Field(..., example="SKU123")
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[str] = None
    active: Optional[bool] = True

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[str] = None
    active: Optional[bool] = None

class ProductOut(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# Webhook schemas
class WebhookBase(BaseModel):
    url: HttpUrl
    event: str = Field(..., example="product_imported")
    enabled: bool = True

class WebhookCreate(WebhookBase):
    pass

class WebhookOut(WebhookBase):
    id: int

    class Config:
        orm_mode = True

# Progress schema
class ProgressOut(BaseModel):
    task_id: str
    status: str
    progress: float
    message: Optional[str] = None
