from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

class Database:
    client: AsyncIOMotorClient = None
    
db = Database()

async def connect_to_mongo():
    """Connect to MongoDB"""
    db.client = AsyncIOMotorClient(settings.MONGODB_URL)
    
async def close_mongo_connection():
    """Close MongoDB connection"""
    if db.client:
        db.client.close()

def get_database():
    """Get database instance"""
    return db.client[settings.DB_NAME]