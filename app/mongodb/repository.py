from .schemas import MoodEntry, ThoughtEntry, StateSnapshot
from ..database import mongo_db
from typing import List, Optional, Dict, Any
   
class MongoRepository:
    @staticmethod
    async def save_mood_entry(mood_entry: MoodEntry) -> str:
        result = await mongo_db.mood_entries.insert_one(mood_entry.dict())
        return str(result.inserted_id)
    
    @staticmethod
    async def get_mood_entries(user_id: str, limit: int = 10, skip: int = 0) -> List[MoodEntry]:
        cursor = mongo_db.mood_entries.find({"user_id": user_id}).sort("timestamp", -1).skip(skip).limit(limit)
        return [MoodEntry(**document) for document in await cursor.to_list(length=limit)]
    
    @staticmethod
    async def save_thought_entry(thought_entry: ThoughtEntry) -> str:
        result = await mongo_db.thought_entries.insert_one(thought_entry.dict())
        return str(result.inserted_id)
    
    @staticmethod
    async def get_thought_entries(user_id: str, limit: int = 10, skip: int = 0) -> List[ThoughtEntry]:
        cursor = mongo_db.thought_entries.find({"user_id": user_id}).sort("timestamp", -1).skip(skip).limit(limit)
        return [ThoughtEntry(**document) for document in await cursor.to_list(length=limit)]
    
    @staticmethod
    async def save_state_snapshot(state_snapshot: StateSnapshot) -> str:
        result = await mongo_db.state_snapshots.insert_one(state_snapshot.dict())
        return str(result.inserted_id)
    
    @staticmethod
    async def get_state_snapshots(user_id: str, limit: int = 10, skip: int = 0) -> List[StateSnapshot]:
        cursor = mongo_db.state_snapshots.find({"user_id": user_id}).sort("timestamp", -1).skip(skip).limit(limit)
        return [StateSnapshot(**document) for document in await cursor.to_list(length=limit)]