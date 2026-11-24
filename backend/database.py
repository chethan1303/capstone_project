"""
PI-EWS Database Module.

Provides async MongoDB connection via motor and Beanie ODM initialization.
"""

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from config import settings
from models.user import User
from models.conversation import Conversation
from models.security_event import SecurityEvent


async def init_db() -> None:
    """Initialize the MongoDB connection and Beanie ODM.

    Creates a motor client, selects the database, and initializes
    Beanie with all document models for automatic collection management.
    """
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    database = client[settings.DATABASE_NAME]

    await init_beanie(
        database=database,
        document_models=[User, Conversation, SecurityEvent],
    )
