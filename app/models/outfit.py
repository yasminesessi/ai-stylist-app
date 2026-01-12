from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from app.models.clothing import Occasion, Season

class OutfitRequest(BaseModel):
    """Request model for generating outfit recommendations"""
    user_id: str
    occasion: Occasion
    season: Optional[Season] = None
    weather: Optional[str] = None  # sunny, rainy, cold, hot
    mood: Optional[str] = None  # confident, relaxed, professional, creative
    additional_preferences: Optional[str] = None
    num_suggestions: int = Field(default=3, ge=1, le=10)

class ClothingItemInOutfit(BaseModel):
    """Clothing item reference in an outfit"""
    id: str
    name: str
    category: str
    color: str
    image_url: Optional[str] = None

class OutfitSuggestion(BaseModel):
    """Single outfit suggestion"""
    items: List[ClothingItemInOutfit]
    reasoning: str
    style_description: str
    confidence_score: float = Field(ge=0.0, le=1.0)

class OutfitResponse(BaseModel):
    """Response model for outfit recommendations"""
    request_id: str
    user_id: str
    suggestions: List[OutfitSuggestion]
    timestamp: datetime
    agent_thoughts: Optional[str] = None

class SavedOutfit(BaseModel):
    """Model for saving a favorite outfit"""
    id: str = Field(alias="_id")
    user_id: str
    name: str
    items: List[ClothingItemInOutfit]
    occasion: Occasion
    season: Season
    notes: Optional[str] = None
    created_at: datetime
    last_worn: Optional[datetime] = None
    
    class Config:
        populate_by_name = True