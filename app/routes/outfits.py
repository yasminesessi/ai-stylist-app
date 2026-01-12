from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form
from app.models.outfit import OutfitRequest, OutfitResponse, OutfitSuggestion, ClothingItemInOutfit
from app.agents.outfit_agent import outfit_agent
from app.services.vision_service import vision_service
from app.database.connection import get_database
from bson import ObjectId
from datetime import datetime
from typing import Optional, List
import uuid
import json

router = APIRouter()

@router.post("/recommend", response_model=OutfitResponse)
async def get_outfit_recommendations(request: OutfitRequest):
    """Get AI-powered outfit recommendations based on occasion and preferences"""
    db = get_database()
    
    # Verify user exists
    try:
        user = await db.users.find_one({"_id": ObjectId(request.user_id)})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    
    # Get user's wardrobe
    wardrobe_items = await db.wardrobe.find({"user_id": request.user_id}).to_list(length=1000)
    
    if not wardrobe_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no clothing items in wardrobe. Please add some items first."
        )
    
    # Prepare user profile for the agent
    user_profile = {
        "personality": user.get("personality", {}),
        "style_preferences": user.get("style_preferences", {}),
        "name": user.get("name", "User")
    }
    
    # Prepare request data
    request_data = {
        "occasion": request.occasion,
        "season": request.season,
        "weather": request.weather,
        "mood": request.mood,
        "additional_preferences": request.additional_preferences,
        "num_suggestions": request.num_suggestions
    }
    
    # Call the LangGraph agent
    try:
        result = await outfit_agent.recommend_outfits(
            user_profile=user_profile,
            wardrobe_items=wardrobe_items,
            request=request_data
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating recommendations: {str(e)}"
        )
    
    # Convert suggestions to response format
    suggestions = []
    for suggestion in result.get("suggestions", []):
        # Get full item details
        item_ids = suggestion.get("item_ids", [])
        items = []
        
        for item_id in item_ids:
            try:
                item = await db.wardrobe.find_one({"_id": ObjectId(item_id)})
                if item:
                    items.append(ClothingItemInOutfit(
                        id=str(item["_id"]),
                        name=item["name"],
                        category=item["category"],
                        color=item["color"],
                        image_url=item.get("image_url")
                    ))
            except:
                continue
        
        if items:  # Only include suggestions with valid items
            suggestions.append(OutfitSuggestion(
                items=items,
                reasoning=suggestion.get("reasoning", ""),
                style_description=suggestion.get("style_description", ""),
                confidence_score=suggestion.get("confidence_score", 0.8)
            ))
    
    return OutfitResponse(
        request_id=str(uuid.uuid4()),
        user_id=request.user_id,
        suggestions=suggestions,
        timestamp=datetime.utcnow(),
        agent_thoughts=result.get("reasoning")
    )


@router.post("/recommend-with-inspiration")
async def get_outfit_recommendations_with_inspiration(
    user_id: str = Form(...),
    occasion: str = Form(...),
    inspiration_image: Optional[UploadFile] = File(None),
    season: Optional[str] = Form(None),
    weather: Optional[str] = Form(None),
    mood: Optional[str] = Form(None),
    additional_preferences: Optional[str] = Form(None),
    num_suggestions: int = Form(3)
):
    """
    Get outfit recommendations with an optional inspiration image.
    User can upload a photo of an outfit they like, and the AI will try to 
    create similar looks from their wardrobe.
    """
    db = get_database()
    
    # Verify user exists
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    
    # Get user's wardrobe
    wardrobe_items = await db.wardrobe.find({"user_id": user_id}).to_list(length=1000)
    
    if not wardrobe_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no clothing items in wardrobe. Please add some items first."
        )
    
    # Analyze inspiration image if provided
    inspiration_analysis = None
    if inspiration_image:
        try:
            image_content = await inspiration_image.read()
            inspiration_analysis = await vision_service.analyze_clothing_image(
                image_content, 
                inspiration_image.content_type
            )
        except Exception as e:
            # Continue without inspiration if analysis fails
            inspiration_analysis = None
    
    # Prepare user profile
    user_profile = {
        "personality": user.get("personality", {}),
        "style_preferences": user.get("style_preferences", {}),
        "name": user.get("name", "User")
    }
    
    # Enhance preferences with inspiration
    enhanced_preferences = additional_preferences or ""
    if inspiration_analysis:
        enhanced_preferences += f"\n\nInspiration outfit style: {inspiration_analysis.get('style_tags', [])}. "
        enhanced_preferences += f"Colors: {inspiration_analysis.get('primary_color')}, {inspiration_analysis.get('secondary_colors', [])}. "
        enhanced_preferences += f"Pattern: {inspiration_analysis.get('pattern')}."
    
    # Prepare request data
    request_data = {
        "occasion": occasion,
        "season": season,
        "weather": weather,
        "mood": mood,
        "additional_preferences": enhanced_preferences,
        "num_suggestions": num_suggestions,
        "inspiration": inspiration_analysis
    }
    
    # Call the agent
    try:
        result = await outfit_agent.recommend_outfits(
            user_profile=user_profile,
            wardrobe_items=wardrobe_items,
            request=request_data
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating recommendations: {str(e)}"
        )
    
    # Convert to response format
    suggestions = []
    for suggestion in result.get("suggestions", []):
        item_ids = suggestion.get("item_ids", [])
        items = []
        
        for item_id in item_ids:
            try:
                item = await db.wardrobe.find_one({"_id": ObjectId(item_id)})
                if item:
                    items.append(ClothingItemInOutfit(
                        id=str(item["_id"]),
                        name=item["name"],
                        category=item["category"],
                        color=item["color"],
                        image_url=item.get("image_url")
                    ))
            except:
                continue
        
        if items:
            suggestions.append(OutfitSuggestion(
                items=items,
                reasoning=suggestion.get("reasoning", ""),
                style_description=suggestion.get("style_description", ""),
                confidence_score=suggestion.get("confidence_score", 0.8)
            ))
    
    return {
        "request_id": str(uuid.uuid4()),
        "user_id": user_id,
        "suggestions": [s.model_dump() for s in suggestions],
        "timestamp": datetime.utcnow(),
        "agent_thoughts": result.get("reasoning"),
        "inspiration_analysis": inspiration_analysis
    }


@router.post("/evaluate-outfit")
async def evaluate_outfit_combination(
    user_id: str = Form(...),
    item_ids: str = Form(...),  # Comma-separated item IDs
    occasion: str = Form(...)
):
    """
    Evaluate how well a specific combination of items works together.
    Useful when user wants feedback on their own outfit choices.
    """
    db = get_database()
    
    # Verify user exists
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    
    # Parse item IDs
    item_id_list = [id.strip() for id in item_ids.split(",")]
    
    # Get items
    outfit_items = []
    for item_id in item_id_list:
        try:
            item = await db.wardrobe.find_one({"_id": ObjectId(item_id)})
            if item:
                outfit_items.append({
                    "name": item["name"],
                    "category": item["category"],
                    "color": item["color"],
                    "style_tags": item.get("style_tags", []),
                    "pattern": item.get("ai_analysis", {}).get("pattern", "unknown")
                })
        except:
            continue
    
    if not outfit_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid items found"
        )
    
    # Get user preferences
    user_preferences = user.get("style_preferences", {})
    
    # Use vision service to evaluate
    evaluation = await vision_service.compare_outfits(
        outfit_items=outfit_items,
        occasion=occasion,
        user_preferences=user_preferences
    )
    
    return {
        "user_id": user_id,
        "items": outfit_items,
        "occasion": occasion,
        "evaluation": evaluation
    }


@router.get("/history/{user_id}")
async def get_outfit_history(user_id: str, limit: int = 10):
    """Get user's outfit recommendation history"""
    db = get_database()
    
    # Get saved outfits (if you implement this collection)
    saved_outfits = await db.saved_outfits.find(
        {"user_id": user_id}
    ).sort("created_at", -1).limit(limit).to_list(length=limit)
    
    return {
        "user_id": user_id,
        "history": saved_outfits,
        "count": len(saved_outfits)
    }


@router.post("/save-outfit")
async def save_outfit(
    user_id: str = Form(...),
    name: str = Form(...),
    item_ids: str = Form(...),
    occasion: str = Form(...),
    season: str = Form(...),
    notes: Optional[str] = Form(None)
):
    """
    Save a favorite outfit combination for quick access later.
    """
    db = get_database()
    
    # Verify user exists
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    
    # Parse item IDs
    item_id_list = [id.strip() for id in item_ids.split(",")]
    
    # Get full item details
    items = []
    for item_id in item_id_list:
        try:
            item = await db.wardrobe.find_one({"_id": ObjectId(item_id)})
            if item:
                items.append({
                    "id": str(item["_id"]),
                    "name": item["name"],
                    "category": item["category"],
                    "color": item["color"],
                    "image_url": item.get("image_url")
                })
        except:
            continue
    
    if not items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid items found"
        )
    
    # Save outfit
    saved_outfit = {
        "user_id": user_id,
        "name": name,
        "items": items,
        "occasion": occasion,
        "season": season,
        "notes": notes,
        "created_at": datetime.utcnow(),
        "last_worn": None,
        "wear_count": 0
    }
    
    result = await db.saved_outfits.insert_one(saved_outfit)
    saved_outfit["_id"] = str(result.inserted_id)
    
    return saved_outfit


@router.put("/outfit/{outfit_id}/worn")
async def mark_outfit_worn(outfit_id: str):
    """
    Mark an outfit as worn (updates last_worn date and wear_count).
    Useful for tracking outfit usage.
    """
    db = get_database()
    
    try:
        obj_id = ObjectId(outfit_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid outfit ID format"
        )
    
    result = await db.saved_outfits.update_one(
        {"_id": obj_id},
        {
            "$set": {"last_worn": datetime.utcnow()},
            "$inc": {"wear_count": 1}
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Outfit not found"
        )
    
    updated_outfit = await db.saved_outfits.find_one({"_id": obj_id})
    updated_outfit["_id"] = str(updated_outfit["_id"])
    
    return updated_outfit


@router.delete("/outfit/{outfit_id}")
async def delete_saved_outfit(outfit_id: str):
    """Delete a saved outfit"""
    db = get_database()
    
    try:
        obj_id = ObjectId(outfit_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid outfit ID format"
        )
    
    result = await db.saved_outfits.delete_one({"_id": obj_id})
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Outfit not found"
        )
    
    return {"message": "Outfit deleted successfully"}