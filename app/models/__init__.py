"""Pydantic models for API request/response"""

from .user import UserCreate, UserUpdate, UserResponse, PersonalityTraits, StylePreferences
from .clothing import (
    ClothingCreate, 
    ClothingUpdate, 
    ClothingResponse, 
    ClothingCategory, 
    Season, 
    Occasion,
    ClothingAnalysis 
)
from .outfit import (
    OutfitRequest, 
    OutfitResponse, 
    OutfitSuggestion, 
    ClothingItemInOutfit,
    SavedOutfit
)

__all__ = [
    # User models
    "UserCreate",
    "UserUpdate", 
    "UserResponse",
    "PersonalityTraits",
    "StylePreferences",
    
    # Clothing models
    "ClothingCreate",
    "ClothingUpdate",
    "ClothingResponse",
    "ClothingCategory",
    "Season",
    "Occasion",
    "ClothingAnalysis",
    
    # Outfit models
    "OutfitRequest",
    "OutfitResponse",
    "OutfitSuggestion",
    "ClothingItemInOutfit",
    "SavedOutfit", 
]