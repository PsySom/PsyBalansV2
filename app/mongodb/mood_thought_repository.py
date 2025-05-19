"""
Репозиторий для работы с коллекциями MongoDB для хранения записей дневников настроения и мыслей.
"""
import logging
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Dict, Any, List, Optional, Tuple, Union
from bson import ObjectId

from app.core.database.mongodb import get_mongodb
from app.mongodb.mood_thought_schemas import (
    create_timestamped_document,
    MOOD_ENTRIES_SCHEMA,
    THOUGHT_ENTRIES_SCHEMA,
    MOOD_ENTRIES_INDEXES,
    THOUGHT_ENTRIES_INDEXES
)

logger = logging.getLogger(__name__)

# Названия коллекций
MOOD_ENTRIES_COLLECTION = "mood_entries"
THOUGHT_ENTRIES_COLLECTION = "thought_entries"


async def init_mood_thought_collections():
    """
    Инициализирует коллекции для хранения записей настроения и мыслей.
    Создает коллекции, если они не существуют, и добавляет валидаторы и индексы.
    """
    try:
        db = await get_mongodb()
        if db is None:
            logger.warning("MongoDB not available, skipping mood_thought collections initialization")
            return
        
        # Получаем список существующих коллекций
        try:
            collections = await db.list_collection_names()
        except Exception as e:
            logger.warning(f"Could not get collection names: {e}")
            collections = []
        
        try:
            # Инициализируем коллекцию mood_entries
            if MOOD_ENTRIES_COLLECTION not in collections:
                await db.create_collection(
                    MOOD_ENTRIES_COLLECTION,
                    **MOOD_ENTRIES_SCHEMA
                )
                logger.info(f"Created collection {MOOD_ENTRIES_COLLECTION}")
            else:
                # Обновляем валидатор, если коллекция уже существует
                await db.command({
                    "collMod": MOOD_ENTRIES_COLLECTION,
                    **MOOD_ENTRIES_SCHEMA
                })
                logger.info(f"Updated validation schema for {MOOD_ENTRIES_COLLECTION}")
            
            # Инициализируем коллекцию thought_entries
            if THOUGHT_ENTRIES_COLLECTION not in collections:
                await db.create_collection(
                    THOUGHT_ENTRIES_COLLECTION,
                    **THOUGHT_ENTRIES_SCHEMA
                )
                logger.info(f"Created collection {THOUGHT_ENTRIES_COLLECTION}")
            else:
                # Обновляем валидатор, если коллекция уже существует
                await db.command({
                    "collMod": THOUGHT_ENTRIES_COLLECTION,
                    **THOUGHT_ENTRIES_SCHEMA
                })
                logger.info(f"Updated validation schema for {THOUGHT_ENTRIES_COLLECTION}")
            
            # Создаем индексы для mood_entries
            for index in MOOD_ENTRIES_INDEXES:
                await db[MOOD_ENTRIES_COLLECTION].create_index(
                    index["key"], 
                    name=index.get("name")
                )
            logger.info(f"Created indexes for {MOOD_ENTRIES_COLLECTION}")
            
            # Создаем индексы для thought_entries
            for index in THOUGHT_ENTRIES_INDEXES:
                await db[THOUGHT_ENTRIES_COLLECTION].create_index(
                    index["key"], 
                    name=index.get("name")
                )
            logger.info(f"Created indexes for {THOUGHT_ENTRIES_COLLECTION}")
        except Exception as e:
            logger.error(f"Error initializing mood_thought collections: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize mood_thought collections: {e}")


# Функции для работы с коллекцией mood_entries

async def create_mood_entry(
    user_id: str,
    mood_score: float,
    emotions: List[Dict[str, Any]],
    timestamp: datetime = None,
    triggers: List[str] = None,
    physical_sensations: List[str] = None,
    body_areas: List[str] = None,
    context: str = None,
    notes: str = None
) -> str:
    """
    Создает новую запись настроения и эмоций.
    Возвращает ID созданной записи.
    """
    db = await get_mongodb()
    
    mood_entry = {
        "user_id": user_id,
        "mood_score": mood_score,
        "emotions": emotions,
        "timestamp": timestamp or datetime.utcnow(),
    }
    
    # Добавляем опциональные поля, если они предоставлены
    if triggers:
        mood_entry["triggers"] = triggers
    if physical_sensations:
        mood_entry["physical_sensations"] = physical_sensations
    if body_areas:
        mood_entry["body_areas"] = body_areas
    if context:
        mood_entry["context"] = context
    if notes:
        mood_entry["notes"] = notes
    
    # Добавляем временные метки
    mood_entry = create_timestamped_document(mood_entry)
    
    result = await db[MOOD_ENTRIES_COLLECTION].insert_one(mood_entry)
    return str(result.inserted_id)


async def get_mood_entry(entry_id: str) -> Optional[Dict[str, Any]]:
    """
    Получает одну запись настроения по ID.
    """
    db = await get_mongodb()
    result = await db[MOOD_ENTRIES_COLLECTION].find_one({"_id": ObjectId(entry_id)})
    if result:
        result["_id"] = str(result["_id"])
    return result


async def get_user_mood_entries(
    user_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    skip: int = 0,
    sort_order: int = -1  # -1 для сортировки от новых к старым
) -> List[Dict[str, Any]]:
    """
    Получает записи настроения пользователя с возможностью фильтрации по датам.
    """
    db = await get_mongodb()
    
    # Создаем базовый запрос
    query = {"user_id": user_id}
    
    # Добавляем фильтры по датам, если они указаны
    if start_date or end_date:
        date_query = {}
        if start_date:
            date_query["$gte"] = start_date
        if end_date:
            date_query["$lte"] = end_date
        query["timestamp"] = date_query
    
    # Выполняем запрос с пагинацией и сортировкой
    cursor = db[MOOD_ENTRIES_COLLECTION].find(query)
    cursor = cursor.sort("timestamp", sort_order).skip(skip).limit(limit)
    
    results = await cursor.to_list(length=limit)
    
    # Преобразуем ObjectId в строки для совместимости с JSON
    for result in results:
        result["_id"] = str(result["_id"])
    
    return results


async def update_mood_entry(entry_id: str, updates: Dict[str, Any]) -> bool:
    """
    Обновляет запись настроения.
    Возвращает True, если запись была обновлена, иначе False.
    """
    db = await get_mongodb()
    
    # Добавляем updated_at
    updates["updated_at"] = datetime.utcnow()
    
    result = await db[MOOD_ENTRIES_COLLECTION].update_one(
        {"_id": ObjectId(entry_id)},
        {"$set": updates}
    )
    
    return result.modified_count > 0


async def delete_mood_entry(entry_id: str) -> bool:
    """
    Удаляет запись настроения.
    Возвращает True, если запись была удалена, иначе False.
    """
    db = await get_mongodb()
    result = await db[MOOD_ENTRIES_COLLECTION].delete_one({"_id": ObjectId(entry_id)})
    return result.deleted_count > 0


async def get_mood_statistics(
    user_id: str,
    period: str = "week",  # "day", "week", "month", "year", "all"
    end_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Получает статистику настроения пользователя за указанный период.
    """
    db = await get_mongodb()
    
    # Определяем дату начала периода
    if end_date is None:
        end_date = datetime.utcnow()
    
    if period == "day":
        start_date = end_date - timedelta(days=1)
    elif period == "week":
        start_date = end_date - timedelta(days=7)
    elif period == "month":
        start_date = end_date - timedelta(days=30)
    elif period == "year":
        start_date = end_date - timedelta(days=365)
    elif period == "all":
        start_date = datetime.min
    else:
        raise ValueError(f"Неподдерживаемый период: {period}")
    
    # Формируем запрос
    query = {
        "user_id": user_id,
        "timestamp": {
            "$gte": start_date,
            "$lte": end_date
        }
    }
    
    # Получаем все записи за период
    cursor = db[MOOD_ENTRIES_COLLECTION].find(query)
    entries = await cursor.to_list(length=1000)  # Ограничение на количество записей
    
    # Рассчитываем статистику
    if not entries:
        return {
            "period": period,
            "start_date": start_date,
            "end_date": end_date,
            "count": 0,
            "mood_avg": None,
            "mood_min": None,
            "mood_max": None,
            "top_emotions": [],
            "top_triggers": []
        }
    
    # Рассчитываем основные метрики
    mood_scores = [entry["mood_score"] for entry in entries]
    mood_avg = sum(mood_scores) / len(mood_scores)
    mood_min = min(mood_scores)
    mood_max = max(mood_scores)
    
    # Анализируем эмоции
    emotion_counter = {}
    for entry in entries:
        if "emotions" in entry and entry["emotions"]:
            for emotion in entry["emotions"]:
                name = emotion["name"]
                if name in emotion_counter:
                    emotion_counter[name] += 1
                else:
                    emotion_counter[name] = 1
    
    top_emotions = sorted(emotion_counter.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Анализируем триггеры
    trigger_counter = {}
    for entry in entries:
        if "triggers" in entry and entry["triggers"]:
            for trigger in entry["triggers"]:
                if trigger in trigger_counter:
                    trigger_counter[trigger] += 1
                else:
                    trigger_counter[trigger] = 1
    
    top_triggers = sorted(trigger_counter.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        "period": period,
        "start_date": start_date,
        "end_date": end_date,
        "count": len(entries),
        "mood_avg": mood_avg,
        "mood_min": mood_min,
        "mood_max": mood_max,
        "top_emotions": [{"name": name, "count": count} for name, count in top_emotions],
        "top_triggers": [{"name": name, "count": count} for name, count in top_triggers]
    }


# Функции для работы с коллекцией thought_entries

async def create_thought_entry(
    user_id: str,
    situation: str,
    automatic_thoughts: List[Dict[str, Any]],
    emotions: List[Dict[str, Any]],
    timestamp: datetime = None,
    evidence_for: List[str] = None,
    evidence_against: List[str] = None,
    balanced_thought: str = None,
    new_belief_level: float = None,
    action_plan: str = None
) -> str:
    """
    Создает новую запись мыслей.
    Возвращает ID созданной записи.
    """
    db = await get_mongodb()
    
    thought_entry = {
        "user_id": user_id,
        "situation": situation,
        "automatic_thoughts": automatic_thoughts,
        "emotions": emotions,
        "timestamp": timestamp or datetime.utcnow(),
    }
    
    # Добавляем опциональные поля, если они предоставлены
    if evidence_for:
        thought_entry["evidence_for"] = evidence_for
    if evidence_against:
        thought_entry["evidence_against"] = evidence_against
    if balanced_thought:
        thought_entry["balanced_thought"] = balanced_thought
    if new_belief_level is not None:
        thought_entry["new_belief_level"] = new_belief_level
    if action_plan:
        thought_entry["action_plan"] = action_plan
    
    # Добавляем временные метки
    thought_entry = create_timestamped_document(thought_entry)
    
    result = await db[THOUGHT_ENTRIES_COLLECTION].insert_one(thought_entry)
    return str(result.inserted_id)


async def get_thought_entry(entry_id: str) -> Optional[Dict[str, Any]]:
    """
    Получает одну запись мыслей по ID.
    """
    db = await get_mongodb()
    result = await db[THOUGHT_ENTRIES_COLLECTION].find_one({"_id": ObjectId(entry_id)})
    if result:
        result["_id"] = str(result["_id"])
    return result


async def get_user_thought_entries(
    user_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    skip: int = 0,
    sort_order: int = -1  # -1 для сортировки от новых к старым
) -> List[Dict[str, Any]]:
    """
    Получает записи мыслей пользователя с возможностью фильтрации по датам.
    """
    db = await get_mongodb()
    
    # Создаем базовый запрос
    query = {"user_id": user_id}
    
    # Добавляем фильтры по датам, если они указаны
    if start_date or end_date:
        date_query = {}
        if start_date:
            date_query["$gte"] = start_date
        if end_date:
            date_query["$lte"] = end_date
        query["timestamp"] = date_query
    
    # Выполняем запрос с пагинацией и сортировкой
    cursor = db[THOUGHT_ENTRIES_COLLECTION].find(query)
    cursor = cursor.sort("timestamp", sort_order).skip(skip).limit(limit)
    
    results = await cursor.to_list(length=limit)
    
    # Преобразуем ObjectId в строки для совместимости с JSON
    for result in results:
        result["_id"] = str(result["_id"])
    
    return results


async def update_thought_entry(entry_id: str, updates: Dict[str, Any]) -> bool:
    """
    Обновляет запись мыслей.
    Возвращает True, если запись была обновлена, иначе False.
    """
    db = await get_mongodb()
    
    # Добавляем updated_at
    updates["updated_at"] = datetime.utcnow()
    
    result = await db[THOUGHT_ENTRIES_COLLECTION].update_one(
        {"_id": ObjectId(entry_id)},
        {"$set": updates}
    )
    
    return result.modified_count > 0


async def delete_thought_entry(entry_id: str) -> bool:
    """
    Удаляет запись мыслей.
    Возвращает True, если запись была удалена, иначе False.
    """
    db = await get_mongodb()
    result = await db[THOUGHT_ENTRIES_COLLECTION].delete_one({"_id": ObjectId(entry_id)})
    return result.deleted_count > 0


async def get_thought_statistics(
    user_id: str,
    period: str = "week",  # "day", "week", "month", "year", "all"
    end_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Получает статистику мыслей пользователя за указанный период.
    """
    db = await get_mongodb()
    
    # Определяем дату начала периода
    if end_date is None:
        end_date = datetime.utcnow()
    
    if period == "day":
        start_date = end_date - timedelta(days=1)
    elif period == "week":
        start_date = end_date - timedelta(days=7)
    elif period == "month":
        start_date = end_date - timedelta(days=30)
    elif period == "year":
        start_date = end_date - timedelta(days=365)
    elif period == "all":
        start_date = datetime.min
    else:
        raise ValueError(f"Неподдерживаемый период: {period}")
    
    # Формируем запрос
    query = {
        "user_id": user_id,
        "timestamp": {
            "$gte": start_date,
            "$lte": end_date
        }
    }
    
    # Получаем все записи за период
    cursor = db[THOUGHT_ENTRIES_COLLECTION].find(query)
    entries = await cursor.to_list(length=1000)  # Ограничение на количество записей
    
    # Рассчитываем статистику
    if not entries:
        return {
            "period": period,
            "start_date": start_date,
            "end_date": end_date,
            "count": 0,
            "top_distortions": [],
            "belief_change_avg": None,
            "emotions_frequency": []
        }
    
    # Анализируем когнитивные искажения
    distortion_counter = {}
    belief_changes = []
    emotion_counter = {}
    
    for entry in entries:
        # Анализируем когнитивные искажения
        if "automatic_thoughts" in entry and entry["automatic_thoughts"]:
            for thought in entry["automatic_thoughts"]:
                if "cognitive_distortions" in thought and thought["cognitive_distortions"]:
                    for distortion in thought["cognitive_distortions"]:
                        if distortion in distortion_counter:
                            distortion_counter[distortion] += 1
                        else:
                            distortion_counter[distortion] = 1
        
        # Анализируем изменения веры в мысли
        if ("automatic_thoughts" in entry and entry["automatic_thoughts"] and
            "new_belief_level" in entry and entry["new_belief_level"] is not None):
            
            initial_level = entry["automatic_thoughts"][0].get("belief_level", 0)
            new_level = entry["new_belief_level"]
            belief_changes.append(initial_level - new_level)
        
        # Анализируем эмоции
        if "emotions" in entry and entry["emotions"]:
            for emotion in entry["emotions"]:
                name = emotion["name"]
                if name in emotion_counter:
                    emotion_counter[name] += 1
                else:
                    emotion_counter[name] = 1
    
    top_distortions = sorted(distortion_counter.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Рассчитываем среднее изменение веры в мысли
    belief_change_avg = sum(belief_changes) / len(belief_changes) if belief_changes else None
    
    # Формируем статистику по эмоциям
    emotions_frequency = sorted(emotion_counter.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        "period": period,
        "start_date": start_date,
        "end_date": end_date,
        "count": len(entries),
        "top_distortions": [{"name": name, "count": count} for name, count in top_distortions],
        "belief_change_avg": belief_change_avg,
        "emotions_frequency": [{"name": name, "count": count} for name, count in emotions_frequency]
    }


# Вспомогательные функции для анализа данных

async def get_user_mood_trends(
    user_id: str,
    interval: str = "day",  # "day", "week", "month"
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 30  # Ограничение на количество точек данных
) -> List[Dict[str, Any]]:
    """
    Получает тренды настроения пользователя с агрегацией по интервалам.
    """
    db = await get_mongodb()
    
    # Определяем даты
    if end_date is None:
        end_date = datetime.utcnow()
    
    if start_date is None:
        if interval == "day":
            start_date = end_date - timedelta(days=limit)
        elif interval == "week":
            start_date = end_date - timedelta(weeks=limit)
        elif interval == "month":
            start_date = end_date - timedelta(days=limit * 30)
        else:
            raise ValueError(f"Неподдерживаемый интервал: {interval}")
    
    # Определяем группировку для агрегации
    if interval == "day":
        date_format = "%Y-%m-%d"
        date_trunc = {
            "$dateToString": {
                "format": date_format,
                "date": "$timestamp"
            }
        }
    elif interval == "week":
        # MongoDB не имеет встроенной функции для недель, используем дни и группировку
        date_format = "%Y-%m-%d"
        date_trunc = {
            "$dateToString": {
                "format": date_format,
                "date": {
                    "$subtract": [
                        "$timestamp",
                        {
                            "$multiply": [
                                {
                                    "$dayOfWeek": "$timestamp"
                                },
                                86400000  # миллисекунды в дне
                            ]
                        }
                    ]
                }
            }
        }
    elif interval == "month":
        date_format = "%Y-%m"
        date_trunc = {
            "$dateToString": {
                "format": date_format,
                "date": "$timestamp"
            }
        }
    else:
        raise ValueError(f"Неподдерживаемый интервал: {interval}")
    
    # Формируем запрос агрегации
    pipeline = [
        {
            "$match": {
                "user_id": user_id,
                "timestamp": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            }
        },
        {
            "$group": {
                "_id": date_trunc,
                "avg_mood": {"$avg": "$mood_score"},
                "min_mood": {"$min": "$mood_score"},
                "max_mood": {"$max": "$mood_score"},
                "count": {"$sum": 1},
                "date": {"$first": "$timestamp"}
            }
        },
        {
            "$sort": {"date": 1}
        },
        {
            "$project": {
                "_id": 0,
                "period": "$_id",
                "avg_mood": 1,
                "min_mood": 1,
                "max_mood": 1,
                "count": 1,
                "date": 1
            }
        }
    ]
    
    result = await db[MOOD_ENTRIES_COLLECTION].aggregate(pipeline).to_list(length=limit)
    return result