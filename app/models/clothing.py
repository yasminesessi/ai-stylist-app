from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class ClothingCategory(str, Enum):
    TOP = "top"
    BOTTOM = "bottom"
    DRESS = "dress"
    OUTERWEAR = "outerwear"
    SHOES = "shoes"
    ACCESSORY = "accessory"

class Season(str, Enum):
    SPRING = "spring"
    SUMMER = "summer"
    FALL = "fall"
    WINTER = "winter"
    ALL_SEASON = "all_season"

class Occasion(str, Enum):
    CASUAL = "casual"
    BUSINESS = "business"
    FORMAL = "formal"
    SPORTS = "sports"
    PARTY = "party"
    DATE = "date"

class ClothingCreate(BaseModel):
    """Model for creating a clothing item manually"""
    user_id: str
    name: str = Field(..., min_length=1, max_length=100)
    category: ClothingCategory
    color: str
    secondary_colors: List[str] = []
    brand: Optional[str] = None
    seasons: List[Season] = [Season.ALL_SEASON]
    occasions: List[Occasion] = [Occasion.CASUAL]
    style_tags: List[str] = []  # minimalist, vintage, streetwear, etc.
    image_url: Optional[str] = None
    notes: Optional[str] = None

class ClothingUpdate(BaseModel):
    """Model for updating a clothing item"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    color: Optional[str] = None
    secondary_colors: Optional[List[str]] = None
    brand: Optional[str] = None
    seasons: Optional[List[Season]] = None
    occasions: Optional[List[Occasion]] = None
    style_tags: Optional[List[str]] = None
    image_url: Optional[str] = None
    notes: Optional[str] = None

class ClothingResponse(BaseModel):
    """Model for clothing response"""
    id: str = Field(alias="_id")
    user_id: str
    name: str
    category: ClothingCategory
    color: str
    secondary_colors: List[str]
    brand: Optional[str]
    seasons: List[Season]
    occasions: List[Occasion]
    style_tags: List[str]
    image_url: Optional[str]
    notes: Optional[str]
    ai_analysis: Optional[Dict[str, Any]] = None 
    created_at: datetime
    updated_at: datetime
    
    class Config:
        populate_by_name = True


class ClothingAnalysis(BaseModel):
    """Model for AI vision analysis results"""
    name: str
    category: str
    primary_color: str
    secondary_colors: List[str] = []
    seasons: List[str] = []
    occasions: List[str] = []
    style_tags: List[str] = []
    brand: Optional[str] = None
    pattern: str = "unknown"
    material_guess: str = "unknown"
    confidence: float = 0.8