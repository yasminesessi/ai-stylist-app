from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form
from app.models.clothing import ClothingCreate, ClothingUpdate, ClothingResponse, ClothingCategory
from app.database.connection import get_database
from app.services.vision_service import vision_service
from bson import ObjectId
from datetime import datetime
from typing import List, Optional
import json

router = APIRouter()

def serialize_clothing(item: dict) -> dict:
    """Convert MongoDB document to serializable format"""
    if item:
        item["_id"] = str(item["_id"])
    return item

@router.post("/upload-image", response_model=ClothingResponse, status_code=status.HTTP_201_CREATED)
async def add_clothing_from_image(
    user_id: str = Form(...),
    image: UploadFile = File(...),
    additional_notes: Optional[str] = Form(None)
):
    """
    Upload a clothing item image and automatically extract details using Vision AI.
    The AI will identify: category, color, style, season, and occasion suggestions.
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
    
    # Validate image file
    if not image.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    try:
        # Read image content
        image_content = await image.read()
        
        # Analyze image with Vision AI
        analysis = await vision_service.analyze_clothing_image(image_content, image.content_type)
        
        # Store image (you might want to use S3, Cloudinary, etc.)
        # For now, we'll store as base64 or a placeholder URL
        image_url = await vision_service.store_image(image_content, user_id, image.filename)
        
        # Create clothing item from AI analysis
        clothing_dict = {
            "user_id": user_id,
            "name": analysis.get("name", "Clothing Item"),
            "category": analysis.get("category", "top"),
            "color": analysis.get("primary_color", "unknown"),
            "secondary_colors": analysis.get("secondary_colors", []),
            "brand": analysis.get("brand"),  # AI might detect brand
            "seasons": analysis.get("seasons", ["all_season"]),
            "occasions": analysis.get("occasions", ["casual"]),
            "style_tags": analysis.get("style_tags", []),
            "image_url": image_url,
            "notes": additional_notes,
            "ai_analysis": analysis,  # Store full AI analysis for reference
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await db.wardrobe.insert_one(clothing_dict)
        created_item = await db.wardrobe.find_one({"_id": result.inserted_id})
        
        return serialize_clothing(created_item)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing image: {str(e)}"
        )

@router.post("/upload-multiple", status_code=status.HTTP_201_CREATED)
async def add_multiple_clothing_from_images(
    user_id: str = Form(...),
    images: List[UploadFile] = File(...)
):
    """
    Upload multiple clothing item images at once.
    Useful for users setting up their wardrobe quickly.
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
    
    results = []
    errors = []
    
    for idx, image in enumerate(images):
        try:
            # Validate image file
            if not image.content_type.startswith('image/'):
                errors.append({"file": image.filename, "error": "Not an image file"})
                continue
            
            # Read and analyze image
            image_content = await image.read()
            analysis = await vision_service.analyze_clothing_image(image_content, image.content_type)
            image_url = await vision_service.store_image(image_content, user_id, image.filename)
            
            # Create clothing item
            clothing_dict = {
                "user_id": user_id,
                "name": analysis.get("name", f"Clothing Item {idx + 1}"),
                "category": analysis.get("category", "top"),
                "color": analysis.get("primary_color", "unknown"),
                "secondary_colors": analysis.get("secondary_colors", []),
                "brand": analysis.get("brand"),
                "seasons": analysis.get("seasons", ["all_season"]),
                "occasions": analysis.get("occasions", ["casual"]),
                "style_tags": analysis.get("style_tags", []),
                "image_url": image_url,
                "ai_analysis": analysis,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result = await db.wardrobe.insert_one(clothing_dict)
            created_item = await db.wardrobe.find_one({"_id": result.inserted_id})
            results.append(serialize_clothing(created_item))
            
        except Exception as e:
            errors.append({"file": image.filename, "error": str(e)})
    
    return {
        "success_count": len(results),
        "error_count": len(errors),
        "items": results,
        "errors": errors
    }

@router.post("/", response_model=ClothingResponse, status_code=status.HTTP_201_CREATED)
async def add_clothing_item(clothing: ClothingCreate):
    """Add a new clothing item to wardrobe manually (without image)"""
    db = get_database()
    
    # Verify user exists
    try:
        user = await db.users.find_one({"_id": ObjectId(clothing.user_id)})
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
    
    clothing_dict = clothing.model_dump()
    clothing_dict["created_at"] = datetime.utcnow()
    clothing_dict["updated_at"] = datetime.utcnow()
    
    result = await db.wardrobe.insert_one(clothing_dict)
    created_item = await db.wardrobe.find_one({"_id": result.inserted_id})
    
    return serialize_clothing(created_item)

@router.get("/{item_id}", response_model=ClothingResponse)
async def get_clothing_item(item_id: str):
    """Get a specific clothing item"""
    db = get_database()
    
    try:
        item = await db.wardrobe.find_one({"_id": ObjectId(item_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid item ID format"
        )
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clothing item not found"
        )
    
    return serialize_clothing(item)

@router.get("/user/{user_id}", response_model=List[ClothingResponse])
async def get_user_wardrobe(
    user_id: str,
    category: Optional[ClothingCategory] = None,
    skip: int = 0,
    limit: int = 100
):
    """Get all clothing items for a user, optionally filtered by category"""
    db = get_database()
    
    query = {"user_id": user_id}
    if category:
        query["category"] = category
    
    items = await db.wardrobe.find(query).skip(skip).limit(limit).to_list(length=limit)
    return [serialize_clothing(item) for item in items]

@router.put("/{item_id}", response_model=ClothingResponse)
async def update_clothing_item(item_id: str, clothing_update: ClothingUpdate):
    """Update a clothing item"""
    db = get_database()
    
    try:
        obj_id = ObjectId(item_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid item ID format"
        )
    
    # Check if item exists
    existing_item = await db.wardrobe.find_one({"_id": obj_id})
    if not existing_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clothing item not found"
        )
    
    # Update only provided fields
    update_data = clothing_update.model_dump(exclude_unset=True)
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        await db.wardrobe.update_one(
            {"_id": obj_id},
            {"$set": update_data}
        )
    
    updated_item = await db.wardrobe.find_one({"_id": obj_id})
    return serialize_clothing(updated_item)

@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_clothing_item(item_id: str):
    """Delete a clothing item"""
    db = get_database()
    
    try:
        obj_id = ObjectId(item_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid item ID format"
        )
    
    result = await db.wardrobe.delete_one({"_id": obj_id})
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clothing item not found"
        )
    
    return None

@router.delete("/user/{user_id}/all", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_wardrobe(user_id: str):
    """Delete all clothing items for a user"""
    db = get_database()
    
    await db.wardrobe.delete_many({"user_id": user_id})
    return None