"""
Репозиторий для работы с коллекциями рекомендаций и интегративного дневника в MongoDB.
Содержит функции для CRUD-операций и специализированных запросов.
"""
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
from bson import ObjectId
from pymongo import ReturnDocument
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.database.mongodb import get_mongodb
import logging

logger = logging.getLogger(__name__)
from app.mongodb.recommendations_diary_schemas import (
    RECOMMENDATIONS_SCHEMA, DIARY_ENTRIES_SCHEMA, 
    RECOMMENDATIONS_INDEXES, DIARY_ENTRIES_INDEXES,
    create_timestamped_document
)
from app.mongodb.recommendations_diary_schemas_pydantic import (
    RecommendationCreate, RecommendationUpdate, Recommendation, RecommendationResponse, EffectivenessData,
    DiaryEntryCreate, DiaryEntryUpdate, DiaryEntry
)


async def init_recommendations_diary_collections():
    """
    Инициализирует коллекции для рекомендаций и интегративного дневника в MongoDB
    со схемами валидации и индексами.
    """
    try:
        db = await get_mongodb()
        if db is None:
            logger.warning("MongoDB not available, skipping recommendations_diary collections initialization")
            return
        
        # Получаем список существующих коллекций
        try:
            collections = await db.list_collection_names()
        except Exception as e:
            logger.warning(f"Could not get collection names: {e}")
            collections = []
        
        try:
            # Создание или обновление коллекции recommendations
            if "recommendations" not in collections:
                await db.create_collection("recommendations", **RECOMMENDATIONS_SCHEMA)
                logger.info("Created collection recommendations")
            else:
                # Обновляем валидатор, если коллекция уже существует
                await db.command({
                    "collMod": "recommendations",
                    **RECOMMENDATIONS_SCHEMA
                })
                logger.info("Updated validation schema for recommendations")
            
            # Создание или обновление коллекции diary_entries
            if "diary_entries" not in collections:
                await db.create_collection("diary_entries", **DIARY_ENTRIES_SCHEMA)
                logger.info("Created collection diary_entries")
            else:
                # Обновляем валидатор, если коллекция уже существует
                await db.command({
                    "collMod": "diary_entries",
                    **DIARY_ENTRIES_SCHEMA
                })
                logger.info("Updated validation schema for diary_entries")
            
            # Создание индексов для recommendations
            for index in RECOMMENDATIONS_INDEXES:
                await db.recommendations.create_index(
                    index["key"], 
                    name=index.get("name")
                )
            logger.info("Created indexes for recommendations")
            
            # Создание индексов для diary_entries
            for index in DIARY_ENTRIES_INDEXES:
                await db.diary_entries.create_index(
                    index["key"], 
                    name=index.get("name")
                )
            logger.info("Created indexes for diary_entries")
        except Exception as e:
            logger.error(f"Error initializing recommendations_diary collections: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize recommendations_diary collections: {e}")


class RecommendationRepository:
    """
    Репозиторий для работы с рекомендациями в MongoDB.
    Обеспечивает эффективную работу с контекстом рекомендаций и отслеживание реакций пользователя.
    """
    def __init__(self, db=None):
        """Инициализация с опциональной базой данных."""
        self.db = db

    async def get_db(self):
        """Получение подключения к базе данных MongoDB."""
        if self.db is None:
            self.db = await get_mongodb()
        return self.db
        
    async def create_recommendation(self, recommendation: RecommendationCreate) -> str:
        """
        Создает новую рекомендацию и возвращает её ID.
        
        Args:
            recommendation: Данные для создания рекомендации
        
        Returns:
            Строковый ID созданной рекомендации
        """
        db = await self.get_db()
        recommendation_dict = recommendation.dict()
        recommendation_dict = create_timestamped_document(recommendation_dict)
        
        result = await db.recommendations.insert_one(recommendation_dict)
        return str(result.inserted_id)
    
    async def get_recommendation(self, recommendation_id: str) -> Optional[Recommendation]:
        """
        Получает рекомендацию по ID.
        
        Args:
            recommendation_id: ID рекомендации
        
        Returns:
            Объект рекомендации или None, если не найдена
        """
        db = await self.get_db()
        if not ObjectId.is_valid(recommendation_id):
            return None
        
        recommendation_dict = await db.recommendations.find_one({"_id": ObjectId(recommendation_id)})
        if recommendation_dict:
            return Recommendation.model_validate(recommendation_dict)
        return None
    
    async def update_recommendation(self, recommendation_id: str, update_data: Union[RecommendationUpdate, dict]) -> Optional[Recommendation]:
        """
        Обновляет рекомендацию по ID и возвращает обновленный документ.
        
        Args:
            recommendation_id: ID рекомендации
            update_data: Данные для обновления (словарь или объект RecommendationUpdate)
            
        Returns:
            Обновленный объект рекомендации или None, если не найдена
        """
        db = await self.get_db()
        if not ObjectId.is_valid(recommendation_id):
            return None
        
        if isinstance(update_data, RecommendationUpdate):
            update_dict = update_data.dict(exclude_unset=True)
        else:
            update_dict = update_data
            
        update_dict["updated_at"] = datetime.utcnow()
        
        recommendation_dict = await db.recommendations.find_one_and_update(
            {"_id": ObjectId(recommendation_id)},
            {"$set": update_dict},
            return_document=ReturnDocument.AFTER
        )
        
        if recommendation_dict:
            return Recommendation.model_validate(recommendation_dict)
        return None
    
    async def delete_recommendation(self, recommendation_id: str) -> bool:
        """
        Удаляет рекомендацию по ID и возвращает результат операции.
        
        Args:
            recommendation_id: ID рекомендации
            
        Returns:
            True если удаление успешно, False в противном случае
        """
        db = await self.get_db()
        if not ObjectId.is_valid(recommendation_id):
            return False
        
        result = await db.recommendations.delete_one({"_id": ObjectId(recommendation_id)})
        return result.deleted_count > 0
    
    async def get_user_recommendations(
        self,
        user_id: str, 
        limit: int = 10, 
        skip: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Recommendation]:
        """
        Получает рекомендации пользователя с возможностью фильтрации по дате.
        
        Args:
            user_id: ID пользователя
            limit: Максимальное количество возвращаемых рекомендаций
            skip: Количество рекомендаций для пропуска (для пагинации)
            start_date: Начальная дата для фильтрации
            end_date: Конечная дата для фильтрации
            
        Returns:
            Список объектов рекомендаций
        """
        db = await self.get_db()
        query = {"user_id": user_id}
        
        if start_date or end_date:
            date_query = {}
            if start_date:
                date_query["$gte"] = start_date
            if end_date:
                date_query["$lte"] = end_date
            query["timestamp"] = date_query
        
        cursor = db.recommendations.find(query).sort("timestamp", -1).skip(skip).limit(limit)
        recommendation_dicts = await cursor.to_list(length=limit)
        
        return [Recommendation.model_validate(rec) for rec in recommendation_dicts]
    
    async def get_recommendations_by_type(
        self,
        recommendation_type: str,
        limit: int = 10,
        skip: int = 0
    ) -> List[Recommendation]:
        """
        Получает рекомендации по типу.
        
        Args:
            recommendation_type: Тип рекомендации
            limit: Максимальное количество возвращаемых рекомендаций
            skip: Количество рекомендаций для пропуска (для пагинации)
            
        Returns:
            Список объектов рекомендаций
        """
        db = await self.get_db()
        cursor = db.recommendations.find(
            {"recommendation_type": recommendation_type}
        ).sort("timestamp", -1).skip(skip).limit(limit)
        
        recommendation_dicts = await cursor.to_list(length=limit)
        return [Recommendation.model_validate(rec) for rec in recommendation_dicts]
    
    async def get_recommendations_by_context(
        self, 
        context_filter: Dict[str, Any],
        limit: int = 10,
        skip: int = 0
    ) -> List[Recommendation]:
        """
        Получает рекомендации по фильтрам контекста.
        
        Args:
            context_filter: Словарь с фильтрами для поля context
            limit: Максимальное количество возвращаемых рекомендаций
            skip: Количество рекомендаций для пропуска (для пагинации)
            
        Returns:
            Список объектов рекомендаций
        """
        db = await self.get_db()
        query = {}
        
        # Формируем запрос для фильтрации по полям контекста
        for key, value in context_filter.items():
            query[f"context.{key}"] = value
        
        cursor = db.recommendations.find(query).sort("timestamp", -1).skip(skip).limit(limit)
        recommendation_dicts = await cursor.to_list(length=limit)
        
        return [Recommendation.model_validate(rec) for rec in recommendation_dicts]
    
    async def get_recommendations_by_trigger(
        self,
        trigger_type: str,
        limit: int = 10,
        skip: int = 0
    ) -> List[Recommendation]:
        """
        Получает рекомендации по типу триггера.
        
        Args:
            trigger_type: Тип триггера рекомендации
            limit: Максимальное количество возвращаемых рекомендаций
            skip: Количество рекомендаций для пропуска (для пагинации)
            
        Returns:
            Список объектов рекомендаций
        """
        return await self.get_recommendations_by_context(
            context_filter={"trigger_type": trigger_type},
            limit=limit,
            skip=skip
        )
    
    async def get_recommendations_by_response_status(
        self,
        status: str,
        limit: int = 10,
        skip: int = 0
    ) -> List[Recommendation]:
        """
        Получает рекомендации по статусу ответа пользователя.
        
        Args:
            status: Статус ответа (accepted, declined, postponed, no_response)
            limit: Максимальное количество возвращаемых рекомендаций
            skip: Количество рекомендаций для пропуска (для пагинации)
            
        Returns:
            Список объектов рекомендаций
        """
        db = await self.get_db()
        cursor = db.recommendations.find(
            {"user_response.status": status}
        ).sort("timestamp", -1).skip(skip).limit(limit)
        
        recommendation_dicts = await cursor.to_list(length=limit)
        return [Recommendation.model_validate(rec) for rec in recommendation_dicts]
    
    async def get_recommendations_by_effectiveness(
        self,
        min_rating: Optional[int] = None,
        min_improvement: Optional[float] = None,
        limit: int = 10,
        skip: int = 0
    ) -> List[Recommendation]:
        """
        Получает рекомендации по уровню эффективности.
        
        Args:
            min_rating: Минимальная оценка пользователя (1-5)
            min_improvement: Минимальное улучшение состояния (-1.0 - 1.0)
            limit: Максимальное количество возвращаемых рекомендаций
            skip: Количество рекомендаций для пропуска (для пагинации)
            
        Returns:
            Список объектов рекомендаций
        """
        db = await self.get_db()
        query = {"effectiveness": {"$exists": True}}
        
        if min_rating is not None:
            query["effectiveness.user_rating"] = {"$gte": min_rating}
            
        if min_improvement is not None:
            query["effectiveness.state_improvement"] = {"$gte": min_improvement}
        
        cursor = db.recommendations.find(query).sort(
            [("effectiveness.user_rating", -1), ("effectiveness.state_improvement", -1)]
        ).skip(skip).limit(limit)
        
        recommendation_dicts = await cursor.to_list(length=limit)
        return [Recommendation.model_validate(rec) for rec in recommendation_dicts]
    
    async def record_user_response(
        self,
        recommendation_id: str,
        response: RecommendationResponse
    ) -> Optional[Recommendation]:
        """
        Записывает реакцию пользователя на рекомендацию.
        
        Args:
            recommendation_id: ID рекомендации
            response: Данные о реакции пользователя
            
        Returns:
            Обновленный объект рекомендации или None в случае ошибки
        """
        # Преобразуем ответ в словарь для обновления
        user_response = {
            "status": response.status,
            "selected_item_id": response.selected_item_id,
            "response_time": datetime.utcnow(),
            "user_feedback": response.user_feedback
        }
        
        # Обновляем рекомендацию
        return await self.update_recommendation(
            recommendation_id,
            {"user_response": user_response}
        )
    
    async def record_effectiveness(
        self,
        recommendation_id: str,
        effectiveness_data: EffectivenessData
    ) -> Optional[Recommendation]:
        """
        Записывает данные об эффективности рекомендации.
        
        Args:
            recommendation_id: ID рекомендации
            effectiveness_data: Данные об эффективности
            
        Returns:
            Обновленный объект рекомендации или None в случае ошибки
        """
        # Преобразуем данные в словарь для обновления
        effectiveness = {
            "state_improvement": effectiveness_data.state_improvement,
            "user_rating": effectiveness_data.user_rating,
            "completion_status": effectiveness_data.completion_status,
            "evaluation_timestamp": datetime.utcnow()
        }
        
        # Обновляем рекомендацию
        return await self.update_recommendation(
            recommendation_id,
            {"effectiveness": effectiveness}
        )
    
    async def get_recommendations_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Получает статистику по рекомендациям.
        Можно фильтровать по пользователю.
        
        Args:
            user_id: ID пользователя (если None, то статистика по всем пользователям)
            
        Returns:
            Словарь со статистикой
        """
        db = await self.get_db()
        match_stage = {}
        if user_id:
            match_stage["user_id"] = user_id
        
        pipeline = [
            {"$match": match_stage},
            {"$group": {
                "_id": "$recommendation_type",
                "count": {"$sum": 1},
                "accepted": {"$sum": {"$cond": [{"$eq": ["$user_response.status", "accepted"]}, 1, 0]}},
                "declined": {"$sum": {"$cond": [{"$eq": ["$user_response.status", "declined"]}, 1, 0]}},
                "postponed": {"$sum": {"$cond": [{"$eq": ["$user_response.status", "postponed"]}, 1, 0]}},
                "no_response": {"$sum": {"$cond": [{"$eq": ["$user_response.status", "no_response"]}, 1, 0]}},
                "avg_effectiveness": {"$avg": "$effectiveness.state_improvement"},
                "avg_rating": {"$avg": "$effectiveness.user_rating"}
            }},
            {"$project": {
                "recommendation_type": "$_id",
                "_id": 0,
                "count": 1,
                "responses": {
                    "accepted": "$accepted",
                    "declined": "$declined",
                    "postponed": "$postponed",
                    "no_response": "$no_response"
                },
                "effectiveness": {
                    "avg_improvement": "$avg_effectiveness",
                    "avg_rating": "$avg_rating"
                }
            }}
        ]
        
        cursor = db.recommendations.aggregate(pipeline)
        results = await cursor.to_list(length=None)
        
        # Дополнительно посчитаем общую статистику
        total_match_stage = {}
        if user_id:
            total_match_stage["user_id"] = user_id
        
        total_pipeline = [
            {"$match": total_match_stage},
            {"$group": {
                "_id": None,
                "total": {"$sum": 1},
                "accepted_total": {"$sum": {"$cond": [{"$eq": ["$user_response.status", "accepted"]}, 1, 0]}},
                "declined_total": {"$sum": {"$cond": [{"$eq": ["$user_response.status", "declined"]}, 1, 0]}},
                "postponed_total": {"$sum": {"$cond": [{"$eq": ["$user_response.status", "postponed"]}, 1, 0]}},
                "no_response_total": {"$sum": {"$cond": [{"$eq": ["$user_response.status", "no_response"]}, 1, 0]}},
                "avg_effectiveness_total": {"$avg": "$effectiveness.state_improvement"},
                "avg_rating_total": {"$avg": "$effectiveness.user_rating"}
            }}
        ]
        
        total_cursor = db.recommendations.aggregate(total_pipeline)
        total_results = await total_cursor.to_list(length=None)
        
        # Агрегация по контексту
        context_pipeline = [
            {"$match": match_stage},
            {"$group": {
                "_id": "$context.trigger_type",
                "count": {"$sum": 1},
                "avg_effectiveness": {"$avg": "$effectiveness.state_improvement"},
                "avg_rating": {"$avg": "$effectiveness.user_rating"}
            }},
            {"$project": {
                "trigger_type": "$_id",
                "_id": 0,
                "count": 1,
                "avg_improvement": "$avg_effectiveness",
                "avg_rating": "$avg_rating"
            }}
        ]
        
        context_cursor = db.recommendations.aggregate(context_pipeline)
        context_results = await context_cursor.to_list(length=None)
        
        # Объединение результатов
        stats = {
            "by_type": results,
            "by_trigger": context_results,
            "total": total_results[0] if total_results else {
                "total": 0,
                "accepted_total": 0,
                "declined_total": 0,
                "postponed_total": 0,
                "no_response_total": 0,
                "avg_effectiveness_total": None,
                "avg_rating_total": None
            }
        }
        
        return stats


class DiaryEntriesRepository:
    """
    Репозиторий для работы с записями интегративного дневника в MongoDB.
    """
    
    def __init__(self, db=None):
        """Инициализация с опциональной базой данных."""
        self.db = db

    async def get_db(self):
        """Получение подключения к базе данных MongoDB."""
        if self.db is None:
            self.db = await get_mongodb()
        return self.db
    async def create_diary_entry(self, entry: DiaryEntryCreate) -> str:
        """
        Создает новую запись в дневнике и возвращает её ID.
        
        Args:
            entry: Данные для создания записи
        
        Returns:
            Строковый ID созданной записи
        """
        db = await self.get_db()
        entry_dict = entry.dict()
        entry_dict = create_timestamped_document(entry_dict)
        
        result = await db.diary_entries.insert_one(entry_dict)
        return str(result.inserted_id)
    
    async def get_diary_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает запись дневника по ID.
        """
        db = await self.get_db()
        if not ObjectId.is_valid(entry_id):
            return None
        
        entry = await db.diary_entries.find_one({"_id": ObjectId(entry_id)})
        return entry
    
    @staticmethod
    async def update_diary_entry(entry_id: str, update_data: DiaryEntryUpdate) -> Optional[Dict[str, Any]]:
        """
        Обновляет запись дневника по ID и возвращает обновленный документ.
        """
        if not ObjectId.is_valid(entry_id):
            return None
        
        update_dict = update_data.dict(exclude_unset=True)
        update_dict["updated_at"] = datetime.utcnow()
        
        entry = await mongo_db.diary_entries.find_one_and_update(
            {"_id": ObjectId(entry_id)},
            {"$set": update_dict},
            return_document=ReturnDocument.AFTER
        )
        return entry
    
    @staticmethod
    async def delete_diary_entry(entry_id: str) -> bool:
        """
        Удаляет запись дневника по ID и возвращает результат операции.
        """
        if not ObjectId.is_valid(entry_id):
            return False
        
        result = await mongo_db.diary_entries.delete_one({"_id": ObjectId(entry_id)})
        return result.deleted_count > 0
    
    @staticmethod
    async def get_user_diary_entries(
        user_id: str, 
        limit: int = 10, 
        skip: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        entry_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Получает записи дневника пользователя с возможностью фильтрации по дате и типу.
        """
        query = {"user_id": user_id}
        
        if start_date or end_date:
            date_query = {}
            if start_date:
                date_query["$gte"] = start_date
            if end_date:
                date_query["$lte"] = end_date
            query["timestamp"] = date_query
        
        if entry_type:
            query["entry_type"] = entry_type
        
        cursor = mongo_db.diary_entries.find(query).sort("timestamp", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
    
    @staticmethod
    async def get_entries_by_session(
        session_id: str,
        limit: int = 10,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Получает записи дневника по ID сессии.
        """
        cursor = mongo_db.diary_entries.find(
            {"session_id": session_id}
        ).sort("timestamp", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
    
    @staticmethod
    async def get_entries_by_type(
        entry_type: str,
        limit: int = 10,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Получает записи дневника по типу.
        """
        cursor = mongo_db.diary_entries.find(
            {"entry_type": entry_type}
        ).sort("timestamp", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
    
    @staticmethod
    async def get_entries_by_mood_range(
        min_mood: float,
        max_mood: float,
        limit: int = 10,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Получает записи дневника по диапазону настроения.
        """
        cursor = mongo_db.diary_entries.find({
            "extracted_data.mood": {"$gte": min_mood, "$lte": max_mood}
        }).sort("timestamp", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
    
    @staticmethod
    async def get_linked_entries(
        entry_id: str,
        limit: int = 10,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Получает записи дневника, связанные с указанной записью.
        """
        if not ObjectId.is_valid(entry_id):
            return []
        
        cursor = mongo_db.diary_entries.find({
            "linked_entries.entry_id": ObjectId(entry_id)
        }).sort("timestamp", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
    
    @staticmethod
    async def add_message_to_conversation(
        entry_id: str,
        role: str,
        content: str
    ) -> Optional[Dict[str, Any]]:
        """
        Добавляет новое сообщение в диалог записи дневника.
        """
        if not ObjectId.is_valid(entry_id):
            return None
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow()
        }
        
        updated_entry = await mongo_db.diary_entries.find_one_and_update(
            {"_id": ObjectId(entry_id)},
            {
                "$push": {"conversation": message},
                "$set": {"updated_at": datetime.utcnow()}
            },
            return_document=ReturnDocument.AFTER
        )
        return updated_entry
    
    @staticmethod
    async def update_extracted_data(
        entry_id: str,
        extracted_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Обновляет извлеченные данные в записи дневника.
        """
        if not ObjectId.is_valid(entry_id):
            return None
        
        updated_entry = await mongo_db.diary_entries.find_one_and_update(
            {"_id": ObjectId(entry_id)},
            {
                "$set": {
                    "extracted_data": extracted_data,
                    "updated_at": datetime.utcnow()
                }
            },
            return_document=ReturnDocument.AFTER
        )
        return updated_entry
    
    @staticmethod
    async def add_linked_entry(
        entry_id: str,
        linked_entry_type: str,
        linked_entry_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Добавляет связанную запись к записи дневника.
        """
        if not ObjectId.is_valid(entry_id) or not ObjectId.is_valid(linked_entry_id):
            return None
        
        linked_entry = {
            "entry_type": linked_entry_type,
            "entry_id": ObjectId(linked_entry_id)
        }
        
        updated_entry = await mongo_db.diary_entries.find_one_and_update(
            {"_id": ObjectId(entry_id)},
            {
                "$push": {"linked_entries": linked_entry},
                "$set": {"updated_at": datetime.utcnow()}
            },
            return_document=ReturnDocument.AFTER
        )
        return updated_entry
    
    @staticmethod
    async def get_diary_stats(user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Получает статистику по дневниковым записям.
        Можно фильтровать по пользователю.
        """
        match_stage = {}
        if user_id:
            match_stage["user_id"] = user_id
        
        # Статистика по типам записей
        type_pipeline = [
            {"$match": match_stage},
            {"$group": {
                "_id": "$entry_type",
                "count": {"$sum": 1}
            }},
            {"$project": {
                "entry_type": "$_id",
                "_id": 0,
                "count": 1
            }}
        ]
        
        type_cursor = mongo_db.diary_entries.aggregate(type_pipeline)
        type_results = await type_cursor.to_list(length=None)
        
        # Статистика по настроению
        mood_pipeline = [
            {"$match": {**match_stage, "extracted_data.mood": {"$exists": True}}},
            {"$group": {
                "_id": None,
                "avg_mood": {"$avg": "$extracted_data.mood"},
                "min_mood": {"$min": "$extracted_data.mood"},
                "max_mood": {"$max": "$extracted_data.mood"},
                "count": {"$sum": 1}
            }},
            {"$project": {
                "_id": 0,
                "avg_mood": 1,
                "min_mood": 1,
                "max_mood": 1,
                "count": 1
            }}
        ]
        
        mood_cursor = mongo_db.diary_entries.aggregate(mood_pipeline)
        mood_results = await mood_cursor.to_list(length=None)
        
        # Статистика по эмоциям
        emotions_pipeline = [
            {"$match": {**match_stage, "extracted_data.emotions": {"$exists": True}}},
            {"$unwind": "$extracted_data.emotions"},
            {"$group": {
                "_id": "$extracted_data.emotions",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}},
            {"$limit": 10},
            {"$project": {
                "emotion": "$_id",
                "_id": 0,
                "count": 1
            }}
        ]
        
        emotions_cursor = mongo_db.diary_entries.aggregate(emotions_pipeline)
        emotions_results = await emotions_cursor.to_list(length=None)
        
        # Статистика по удовлетворенности потребностей
        needs_pipeline = [
            {"$match": {**match_stage, "extracted_data.needs": {"$exists": True}}},
            {"$unwind": "$extracted_data.needs"},
            {"$group": {
                "_id": "$extracted_data.needs.need_id",
                "avg_satisfaction": {"$avg": "$extracted_data.needs.satisfaction_level"},
                "count": {"$sum": 1}
            }},
            {"$project": {
                "need_id": "$_id",
                "_id": 0,
                "avg_satisfaction": 1,
                "count": 1
            }}
        ]
        
        needs_cursor = mongo_db.diary_entries.aggregate(needs_pipeline)
        needs_results = await needs_cursor.to_list(length=None)
        
        # Общая статистика
        total_pipeline = [
            {"$match": match_stage},
            {"$group": {
                "_id": None,
                "total_entries": {"$sum": 1},
                "avg_conversation_length": {"$avg": {"$size": "$conversation"}},
                "linked_entries_count": {"$sum": {"$cond": [{"$isArray": "$linked_entries"}, {"$size": "$linked_entries"}, 0]}}
            }},
            {"$project": {
                "_id": 0,
                "total_entries": 1,
                "avg_conversation_length": 1,
                "linked_entries_count": 1
            }}
        ]
        
        total_cursor = mongo_db.diary_entries.aggregate(total_pipeline)
        total_results = await total_cursor.to_list(length=None)
        
        # Объединение результатов
        stats = {
            "by_type": type_results,
            "mood": mood_results[0] if mood_results else {"avg_mood": None, "min_mood": None, "max_mood": None, "count": 0},
            "top_emotions": emotions_results,
            "needs_satisfaction": needs_results,
            "total": total_results[0] if total_results else {"total_entries": 0, "avg_conversation_length": 0, "linked_entries_count": 0}
        }
        
        return stats