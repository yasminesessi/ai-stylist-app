from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.routes import users, wardrobe, outfits
from app.database.connection import connect_to_mongo, close_mongo_connection
import sys
import os
from pathlib import Path

# Add app to path
sys.path.insert(0, os.path.dirname(__file__))

app = FastAPI(
    title="AI Outfit Recommender API",
    description="Backend API for AI-powered outfit recommendations with vision capabilities",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory if it doesn't exist
uploads_dir = Path("uploads")
uploads_dir.mkdir(exist_ok=True)

# Mount static files for serving uploaded images
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Event handlers
@app.on_event("startup")
async def startup_event():
    await connect_to_mongo()
    print("✅ Connected to MongoDB")
    print("✅ Vision AI enabled (GPT-4o)")
    print("✅ Ready to process wardrobe images")

@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()
    print("❌ Closed MongoDB connection")

# Include routers
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(wardrobe.router, prefix="/api/wardrobe", tags=["Wardrobe"])
app.include_router(outfits.router, prefix="/api/outfits", tags=["Outfits"])

@app.get("/")
async def root():
    return {
        "message": "AI Outfit Recommender API v2.0",
        "features": [
            "Image-based wardrobe management",
            "Vision AI clothing analysis",
            "Personalized outfit recommendations",
            "Inspiration-based outfit suggestions"
        ],
        "docs": "/docs",
        "version": "2.0.0"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "vision_enabled": True,
        "model": "gpt-4o-mini"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)