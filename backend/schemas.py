from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, EmailStr

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Requirements(StrictModel):
    category: Literal['laptop','desktop','tablet'] | None = None
    quantity: int | None = Field(default=None, ge=1, le=100)
    brands: list[str] = Field(default_factory=list, max_length=20)
    min_ram: int | None = Field(default=None, ge=0, le=1024)
    min_storage: int | None = Field(default=None, ge=0, le=100000)
    processor: str | None = Field(default=None, max_length=100)
    storage_type: Literal['SSD','HDD','eMMC'] | None = None
    budget: Decimal | None = Field(default=None, gt=0, le=10000000, decimal_places=3)
    other_preferences: str = Field(default='', max_length=1000)

class SearchInput(StrictModel):
    requirements: Requirements
    max_unit_price: Decimal | None = Field(default=None, gt=0)

class CompareInput(StrictModel):
    offer_ids: list[int] = Field(min_length=1, max_length=100)
    requirements: Requirements

class BudgetInput(StrictModel):
    offer_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=100)
    budget: Decimal = Field(gt=0, le=10000000, decimal_places=3)

class OrderInput(StrictModel):
    proposal_id: str = Field(min_length=16, max_length=64)
    idempotency_key: str = Field(min_length=16, max_length=128)

class DetailInput(StrictModel):
    offer_id: int = Field(gt=0)

class EmailInput(StrictModel):
    order_id: int = Field(gt=0)

class ChatInput(StrictModel):
    message: str = Field(min_length=1, max_length=8000)
    email: EmailStr

class ApprovalInput(StrictModel):
    proposal_id: str
    proposal_hash: str
    approve: bool

class StructuredInput(StrictModel):
    requirements: Requirements
    email: EmailStr


class OfferOutput(StrictModel):
    id: int
    name: str
    category: Literal['laptop','desktop','tablet']
    brand: str | None
    model: str | None
    processor: str | None
    ram_gb: int | None
    storage_gb: int | None
    storage_type: str | None
    screen_size: float | None
    operating_system: str | None
    supplier: str
    price_tnd: str
    stock_status: Literal['in_stock','out_of_stock','unknown']
    available_quantity: int | None
    product_url: str | None
    image_url: str | None
    scraped_at: str
    is_demo: bool

class ComparisonOutput(OfferOutput):
    total_tnd: str
    ranking_reason: str
    stock_note: str

class BudgetOutput(StrictModel):
    total: str
    budget: str
    remaining: str
    valid: bool

class OrderItemOutput(StrictModel):
    name: str
    supplier: str
    quantity: int
    unit_price: str
    subtotal: str

class OrderOutput(StrictModel):
    id: int
    reference: str
    status: str
    total: str
    created_at: str
    email_status: str
    items: list[OrderItemOutput]

class EmailOutput(StrictModel):
    status: Literal['pending','failed','sent','sending','delivery_unknown']
    error: str | None = None
