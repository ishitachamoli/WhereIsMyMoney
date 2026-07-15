from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class CategoryBase(BaseModel):
    name: str = Field(..., max_length=100)
    icon: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=7)
    parent_id: Optional[int] = None


class CategoryCreate(CategoryBase):
    user_id: Optional[int] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    icon: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=7)
    parent_id: Optional[int] = None


class CategoryResponse(CategoryBase):
    model_config = {"from_attributes": True}

    id: int
    user_id: Optional[int] = None
    is_system: bool
    created_at: datetime
    updated_at: datetime
