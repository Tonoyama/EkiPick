from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from .models import PropertyType, PropertyStatus


class UserBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)


class UserCreate(UserBase):
    pass


class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        orm_mode = True


class PropertyBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    location: str = Field(..., min_length=1, max_length=500)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    bedrooms: Optional[int] = Field(None, ge=0)
    bathrooms: Optional[int] = Field(None, ge=0)
    area_sqft: Optional[float] = Field(None, gt=0)
    property_type: PropertyType
    status: PropertyStatus = PropertyStatus.AVAILABLE


class PropertyCreate(PropertyBase):
    owner_id: Optional[int] = None


class PropertyResponse(PropertyBase):
    id: int
    owner_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        orm_mode = True


class PropertyImageBase(BaseModel):
    image_url: str = Field(..., min_length=1, max_length=500)
    caption: Optional[str] = Field(None, max_length=255)
    is_primary: bool = False


class PropertyImageCreate(PropertyImageBase):
    property_id: int


class PropertyImageResponse(PropertyImageBase):
    id: int
    property_id: int
    created_at: datetime

    class Config:
        from_attributes = True
        orm_mode = True


# セッション関連のスキーマ
class SessionCreate(BaseModel):
    data: Optional[dict] = {}


class SessionResponse(BaseModel):
    id: str
    data: dict
    created_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True
        orm_mode = True


class SearchHistoryResponse(BaseModel):
    id: int
    search_type: str
    search_params: dict
    results_count: int
    created_at: datetime

    class Config:
        from_attributes = True
        orm_mode = True


class CommuteHistoryResponse(BaseModel):
    id: int
    from_address: str
    to_address: str
    from_coords: dict
    to_coords: dict
    commute_time: int
    fare: float
    route_data: dict
    created_at: datetime

    class Config:
        from_attributes = True
        orm_mode = True