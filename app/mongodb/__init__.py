"""
Модуль для работы с MongoDB.
Экспортирует репозитории и схемы для работы с данными в MongoDB.
"""

from app.mongodb.base_repository import MongoDBBaseRepository
from app.mongodb.mood_entry_repository import MoodEntryRepository
from app.mongodb.thought_entry_repository import ThoughtEntryRepository
from app.mongodb.activity_evaluation_repository import ActivityEvaluationRepository
from app.mongodb.mood_thought_repository import (
    init_mood_thought_collections,
    create_mood_entry,
    get_mood_entry,
    get_user_mood_entries,
    update_mood_entry,
    delete_mood_entry,
    get_mood_statistics,
    create_thought_entry,
    get_thought_entry,
    get_user_thought_entries,
    update_thought_entry,
    delete_thought_entry,
    get_thought_statistics,
    get_user_mood_trends
)
from app.mongodb.repository import MongoRepository

__all__ = [
    'MongoDBBaseRepository',
    'MoodEntryRepository',
    'ThoughtEntryRepository',
    'ActivityEvaluationRepository',
    'MongoRepository',
    'init_mood_thought_collections',
    'create_mood_entry',
    'get_mood_entry',
    'get_user_mood_entries',
    'update_mood_entry',
    'delete_mood_entry',
    'get_mood_statistics',
    'create_thought_entry',
    'get_thought_entry',
    'get_user_thought_entries',
    'update_thought_entry',
    'delete_thought_entry',
    'get_thought_statistics',
    'get_user_mood_trends'
]