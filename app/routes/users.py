from fastapi import APIRouter, HTTPException, status
from app.models.user import UserCreate, UserUpdate, UserResponse
from app.database.connection import get_database
from bson import ObjectId
from datetime import datetime
from typing import List

router = APIRouter()

def serialize_user(user: dict) -> dict:
    """Convert MongoDB document to serializable format"""
    if user:
        user["_id"] = str(user["_id"])
    return user

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate):
    """Create a new user profile"""
    db = get_database()
    
    # Check if email already exists
    existing_user = await db.users.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    user_dict = user.model_dump()
    user_dict["created_at"] = datetime.utcnow()
    user_dict["updated_at"] = datetime.utcnow()
    
    result = await db.users.insert_one(user_dict)
    created_user = await db.users.find_one({"_id": result.inserted_id})
    
    return serialize_user(created_user)

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """Get user profile by ID"""
    db = get_database()
    
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return serialize_user(user)

@router.get("/", response_model=List[UserResponse])
async def list_users(skip: int = 0, limit: int = 10):
    """List all users"""
    db = get_database()
    
    users = await db.users.find().skip(skip).limit(limit).to_list(length=limit)
    return [serialize_user(user) for user in users]

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, user_update: UserUpdate):
    """Update user profile"""
    db = get_database()
    
    try:
        obj_id = ObjectId(user_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    
    # Check if user exists
    existing_user = await db.users.find_one({"_id": obj_id})
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update only provided fields
    update_data = user_update.model_dump(exclude_unset=True)
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        await db.users.update_one(
            {"_id": obj_id},
            {"$set": update_data}
        )
    
    updated_user = await db.users.find_one({"_id": obj_id})
    return serialize_user(updated_user)

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str):
    """Delete user profile"""
    db = get_database()
    
    try:
        obj_id = ObjectId(user_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    
    result = await db.users.delete_one({"_id": obj_id})
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return None