from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime

class PersonalityTraits(BaseModel):
    """User personality traits for outfit recommendations"""
    bold: int = Field(ge=1, le=10, description="How bold/adventurous in fashion (1-10)")
    minimalist: int = Field(ge=1, le=10, description="Preference for minimalist style (1-10)")
    colorful: int = Field(ge=1, le=10, description="Preference for colorful outfits (1-10)")
    formal: int = Field(ge=1, le=10, description="Preference for formal clothing (1-10)")
    trendy: int = Field(ge=1, le=10, description="How much they follow trends (1-10)")

class StylePreferences(BaseModel):
    """User style preferences"""
    preferred_colors: List[str] = []
    disliked_colors: List[str] = []
    preferred_styles: List[str] = []  # casual, formal, streetwear, bohemian, etc.
    avoid_styles: List[str] = []
    favorite_brands: List[str] = []

class UserCreate(BaseModel):
    """Model for creating a new user"""
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    age: Optional[int] = Field(None, ge=13, le=120)
    gender: Optional[str] = None
    personality: PersonalityTraits
    style_preferences: StylePreferences

class UserUpdate(BaseModel):
    """Model for updating user information"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    age: Optional[int] = Field(None, ge=13, le=120)
    gender: Optional[str] = None
    personality: Optional[PersonalityTraits] = None
    style_preferences: Optional[StylePreferences] = None

class UserResponse(BaseModel):
    """Model for user response"""
    id: str = Field(alias="_id")
    name: str
    email: str
    age: Optional[int] = None
    gender: Optional[str] = None
    personality: PersonalityTraits
    style_preferences: StylePreferences
    created_at: datetime
    updated_at: datetime
    
    class Config:
        populate_by_name = True