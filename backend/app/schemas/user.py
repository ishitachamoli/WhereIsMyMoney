from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class UserBase(BaseModel):
    email: str = Field(..., max_length=255)
    name: str = Field(..., max_length=255)


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    email: Optional[str] = Field(None, max_length=255)
    name: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    model_config = {"from_attributes": True}

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
