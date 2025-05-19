"""
Репозиторий для работы с коллекциями MongoDB для хранения оценок активностей и состояний пользователя.
"""
import logging
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Dict, Any, List, Optional, Tuple, Union
from bson import ObjectId

from app.core.database.mongodb import get_mongodb
from app.mongodb.activity_state_schemas import (
    create_timestamped_document,
    ACTIVITY_EVALUATIONS_SCHEMA,
    STATE_SNAPSHOTS_SCHEMA,
    ACTIVITY_EVALUATIONS_INDEXES,
    STATE_SNAPSHOTS_INDEXES
)

logger = logging.getLogger(__name__)

# Названия коллекций
ACTIVITY_EVALUATIONS_COLLECTION = "activity_evaluations"
STATE_SNAPSHOTS_COLLECTION = "state_snapshots"


async def init_activity_state_collections():
    """
    Инициализирует коллекции для хранения оценок активностей и состояний пользователя.
    Создает коллекции, если они не существуют, и добавляет валидаторы и индексы.
    """
    try:
        db = await get_mongodb()
        if db is None:
            logger.warning("MongoDB not available, skipping activity_state collections initialization")
            return

        # Получаем список существующих коллекций
        try:
            collections = await db.list_collection_names()
        except Exception as e:
            logger.warning(f"Could not get collection names: {e}")
            collections = []
        
        try:
            # Инициализируем коллекцию activity_evaluations
            if ACTIVITY_EVALUATIONS_COLLECTION not in collections:
                await db.create_collection(
                    ACTIVITY_EVALUATIONS_COLLECTION,
                    **ACTIVITY_EVALUATIONS_SCHEMA
                )
                logger.info(f"Created collection {ACTIVITY_EVALUATIONS_COLLECTION}")
            else:
                # Обновляем валидатор, если коллекция уже существует
                await db.command({
                    "collMod": ACTIVITY_EVALUATIONS_COLLECTION,
                    **ACTIVITY_EVALUATIONS_SCHEMA
                })
                logger.info(f"Updated validation schema for {ACTIVITY_EVALUATIONS_COLLECTION}")
            
            # Инициализируем коллекцию state_snapshots
            if STATE_SNAPSHOTS_COLLECTION not in collections:
                await db.create_collection(
                    STATE_SNAPSHOTS_COLLECTION,
                    **STATE_SNAPSHOTS_SCHEMA
                )
                logger.info(f"Created collection {STATE_SNAPSHOTS_COLLECTION}")
            else:
                # Обновляем валидатор, если коллекция уже существует
                await db.command({
                    "collMod": STATE_SNAPSHOTS_COLLECTION,
                    **STATE_SNAPSHOTS_SCHEMA
                })
                logger.info(f"Updated validation schema for {STATE_SNAPSHOTS_COLLECTION}")
            
            # Создаем индексы для activity_evaluations
            for index in ACTIVITY_EVALUATIONS_INDEXES:
                await db[ACTIVITY_EVALUATIONS_COLLECTION].create_index(
                    index["key"], 
                    name=index.get("name")
                )
            logger.info(f"Created indexes for {ACTIVITY_EVALUATIONS_COLLECTION}")
            
            # Создаем индексы для state_snapshots
            for index in STATE_SNAPSHOTS_INDEXES:
                await db[STATE_SNAPSHOTS_COLLECTION].create_index(
                    index["key"], 
                    name=index.get("name")
                )
            logger.info(f"Created indexes for {STATE_SNAPSHOTS_COLLECTION}")
        except Exception as e:
            logger.error(f"Error initializing activity_state collections: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize activity_state collections: {e}")


# Функции для работы с коллекцией activity_evaluations

async def create_activity_evaluation(
    user_id: str,
    activity_id: str,
    timestamp: datetime,
    completion_status: str,
    schedule_id: Optional[str] = None,
    satisfaction_result: Optional[float] = None,
    satisfaction_process: Optional[float] = None,
    energy_impact: Optional[float] = None,
    stress_impact: Optional[float] = None,
    needs_impact: Optional[List[Dict[str, Any]]] = None,
    duration_minutes: Optional[int] = None,
    notes: Optional[str] = None
) -> str:
    """
    Создает новую запись оценки активности.
    Возвращает ID созданной записи.
    """
    db = await get_mongodb()
    
    # Создаем базовый документ
    evaluation = {
        "user_id": user_id,
        "activity_id": activity_id,
        "timestamp": timestamp,
        "completion_status": completion_status
    }
    
    # Добавляем опциональные поля, если они предоставлены
    if schedule_id:
        evaluation["schedule_id"] = schedule_id
    if satisfaction_result is not None:
        evaluation["satisfaction_result"] = satisfaction_result
    if satisfaction_process is not None:
        evaluation["satisfaction_process"] = satisfaction_process
    if energy_impact is not None:
        evaluation["energy_impact"] = energy_impact
    if stress_impact is not None:
        evaluation["stress_impact"] = stress_impact
    if needs_impact:
        evaluation["needs_impact"] = needs_impact
    if duration_minutes is not None:
        evaluation["duration_minutes"] = duration_minutes
    if notes:
        evaluation["notes"] = notes
    
    # Добавляем временные метки
    evaluation = create_timestamped_document(evaluation)
    
    result = await db[ACTIVITY_EVALUATIONS_COLLECTION].insert_one(evaluation)
    return str(result.inserted_id)


async def get_activity_evaluation(evaluation_id: str) -> Optional[Dict[str, Any]]:
    """
    Получает одну оценку активности по ID.
    """
    db = await get_mongodb()
    result = await db[ACTIVITY_EVALUATIONS_COLLECTION].find_one(
        {"_id": ObjectId(evaluation_id)}
    )
    if result:
        result["_id"] = str(result["_id"])
    return result


async def get_user_activity_evaluations(
    user_id: str,
    activity_id: Optional[str] = None,
    schedule_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    completion_status: Optional[str] = None,
    limit: int = 100,
    skip: int = 0,
    sort_order: int = -1  # -1 для сортировки от новых к старым
) -> List[Dict[str, Any]]:
    """
    Получает оценки активностей пользователя с возможностью фильтрации.
    """
    db = await get_mongodb()
    
    # Создаем базовый запрос
    query = {"user_id": user_id}
    
    # Добавляем фильтры, если они указаны
    if activity_id:
        query["activity_id"] = activity_id
    if schedule_id:
        query["schedule_id"] = schedule_id
    if completion_status:
        query["completion_status"] = completion_status
    
    # Добавляем фильтры по датам, если они указаны
    if start_date or end_date:
        date_query = {}
        if start_date:
            date_query["$gte"] = start_date
        if end_date:
            date_query["$lte"] = end_date
        query["timestamp"] = date_query
    
    # Выполняем запрос с пагинацией и сортировкой
    cursor = db[ACTIVITY_EVALUATIONS_COLLECTION].find(query)
    cursor = cursor.sort("timestamp", sort_order).skip(skip).limit(limit)
    
    results = await cursor.to_list(length=limit)
    
    # Преобразуем ObjectId в строки для совместимости с JSON
    for result in results:
        result["_id"] = str(result["_id"])
    
    return results


async def update_activity_evaluation(evaluation_id: str, updates: Dict[str, Any]) -> bool:
    """
    Обновляет оценку активности.
    Возвращает True, если запись была обновлена, иначе False.
    """
    db = await get_mongodb()
    
    # Добавляем updated_at
    updates["updated_at"] = datetime.utcnow()
    
    result = await db[ACTIVITY_EVALUATIONS_COLLECTION].update_one(
        {"_id": ObjectId(evaluation_id)},
        {"$set": updates}
    )
    
    return result.modified_count > 0


async def delete_activity_evaluation(evaluation_id: str) -> bool:
    """
    Удаляет оценку активности.
    Возвращает True, если запись была удалена, иначе False.
    """
    db = await get_mongodb()
    result = await db[ACTIVITY_EVALUATIONS_COLLECTION].delete_one(
        {"_id": ObjectId(evaluation_id)}
    )
    return result.deleted_count > 0


async def get_activity_impact_statistics(
    user_id: str,
    need_id: Optional[str] = None,
    period: str = "month",  # "week", "month", "year"
    end_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Получает статистику влияния активностей на состояние и потребности пользователя.
    """
    db = await get_mongodb()
    
    # Определяем дату начала периода
    if end_date is None:
        end_date = datetime.utcnow()
    
    if period == "week":
        start_date = end_date - timedelta(days=7)
    elif period == "month":
        start_date = end_date - timedelta(days=30)
    elif period == "year":
        start_date = end_date - timedelta(days=365)
    else:
        raise ValueError(f"Неподдерживаемый период: {period}")
    
    # Формируем запрос
    match_query = {
        "user_id": user_id,
        "timestamp": {
            "$gte": start_date,
            "$lte": end_date
        }
    }
    
    # Если указан конкретный need_id, добавляем его в запрос
    if need_id:
        match_query["needs_impact.need_id"] = need_id
    
    # Формируем агрегационный пайплайн для анализа влияния активностей
    pipeline = [
        {"$match": match_query},
        {"$group": {
            "_id": "$activity_id",
            "count": {"$sum": 1},
            "avg_energy_impact": {"$avg": "$energy_impact"},
            "avg_stress_impact": {"$avg": "$stress_impact"},
            "avg_satisfaction_result": {"$avg": "$satisfaction_result"},
            "avg_satisfaction_process": {"$avg": "$satisfaction_process"},
            "total_duration": {"$sum": "$duration_minutes"}
        }},
        {"$sort": {"count": -1}},
        {"$limit": 10}  # Топ-10 активностей
    ]
    
    activity_stats = await db[ACTIVITY_EVALUATIONS_COLLECTION].aggregate(pipeline).to_list(length=10)
    
    # Если указан конкретный need_id, получаем статистику по нему
    need_impact_stats = None
    if need_id:
        need_pipeline = [
            {"$match": match_query},
            {"$unwind": "$needs_impact"},
            {"$match": {"needs_impact.need_id": need_id}},
            {"$group": {
                "_id": "$activity_id",
                "count": {"$sum": 1},
                "avg_impact": {"$avg": "$needs_impact.impact_level"},
            }},
            {"$sort": {"avg_impact": -1}},
            {"$limit": 10}  # Топ-10 активностей по влиянию на потребность
        ]
        need_impact_stats = await db[ACTIVITY_EVALUATIONS_COLLECTION].aggregate(need_pipeline).to_list(length=10)
    
    # Возвращаем статистику
    return {
        "period": period,
        "start_date": start_date,
        "end_date": end_date,
        "total_evaluations": len(activity_stats),
        "activity_statistics": activity_stats,
        "need_impact_statistics": need_impact_stats
    }


# Функции для работы с коллекцией state_snapshots

async def create_state_snapshot(
    user_id: str,
    timestamp: datetime,
    snapshot_type: str,
    mood: Dict[str, Any],
    energy: Dict[str, Any],
    stress: Dict[str, Any],
    needs: Optional[List[Dict[str, Any]]] = None,
    focus_level: Optional[float] = None,
    sleep_quality: Optional[float] = None,
    context_factors: Optional[List[str]] = None
) -> str:
    """
    Создает новую запись снимка состояния пользователя.
    Возвращает ID созданной записи.
    """
    db = await get_mongodb()
    
    # Создаем базовый документ
    snapshot = {
        "user_id": user_id,
        "timestamp": timestamp,
        "snapshot_type": snapshot_type,
        "mood": mood,
        "energy": energy,
        "stress": stress
    }
    
    # Добавляем опциональные поля, если они предоставлены
    if needs:
        snapshot["needs"] = needs
    if focus_level is not None:
        snapshot["focus_level"] = focus_level
    if sleep_quality is not None:
        snapshot["sleep_quality"] = sleep_quality
    if context_factors:
        snapshot["context_factors"] = context_factors
    
    # Добавляем временные метки
    snapshot = create_timestamped_document(snapshot)
    
    result = await db[STATE_SNAPSHOTS_COLLECTION].insert_one(snapshot)
    return str(result.inserted_id)


async def get_state_snapshot(snapshot_id: str) -> Optional[Dict[str, Any]]:
    """
    Получает один снимок состояния по ID.
    """
    db = await get_mongodb()
    result = await db[STATE_SNAPSHOTS_COLLECTION].find_one(
        {"_id": ObjectId(snapshot_id)}
    )
    if result:
        result["_id"] = str(result["_id"])
    return result


async def get_user_state_snapshots(
    user_id: str,
    snapshot_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    skip: int = 0,
    sort_order: int = -1  # -1 для сортировки от новых к старым
) -> List[Dict[str, Any]]:
    """
    Получает снимки состояния пользователя с возможностью фильтрации.
    """
    db = await get_mongodb()
    
    # Создаем базовый запрос
    query = {"user_id": user_id}
    
    # Добавляем фильтр по типу снимка, если он указан
    if snapshot_type:
        query["snapshot_type"] = snapshot_type
    
    # Добавляем фильтры по датам, если они указаны
    if start_date or end_date:
        date_query = {}
        if start_date:
            date_query["$gte"] = start_date
        if end_date:
            date_query["$lte"] = end_date
        query["timestamp"] = date_query
    
    # Выполняем запрос с пагинацией и сортировкой
    cursor = db[STATE_SNAPSHOTS_COLLECTION].find(query)
    cursor = cursor.sort("timestamp", sort_order).skip(skip).limit(limit)
    
    results = await cursor.to_list(length=limit)
    
    # Преобразуем ObjectId в строки для совместимости с JSON
    for result in results:
        result["_id"] = str(result["_id"])
    
    return results


async def update_state_snapshot(snapshot_id: str, updates: Dict[str, Any]) -> bool:
    """
    Обновляет снимок состояния.
    Возвращает True, если запись была обновлена, иначе False.
    """
    db = await get_mongodb()
    
    # Добавляем updated_at
    updates["updated_at"] = datetime.utcnow()
    
    result = await db[STATE_SNAPSHOTS_COLLECTION].update_one(
        {"_id": ObjectId(snapshot_id)},
        {"$set": updates}
    )
    
    return result.modified_count > 0


async def delete_state_snapshot(snapshot_id: str) -> bool:
    """
    Удаляет снимок состояния.
    Возвращает True, если запись была удалена, иначе False.
    """
    db = await get_mongodb()
    result = await db[STATE_SNAPSHOTS_COLLECTION].delete_one(
        {"_id": ObjectId(snapshot_id)}
    )
    return result.deleted_count > 0


async def get_state_trends(
    user_id: str,
    interval: str = "day",  # "day", "week", "month"
    indicators: List[str] = ["mood", "energy", "stress"],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 30  # Ограничение на количество точек данных
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Получает тренды состояния пользователя с агрегацией по интервалам.
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
    
    # Результаты для каждого индикатора
    results = {}
    
    # Определяем поля для каждого индикатора
    indicator_fields = {
        "mood": "$mood.score",
        "energy": "$energy.level",
        "stress": "$stress.level",
        "focus": "$focus_level",
        "sleep": "$sleep_quality"
    }
    
    for indicator in indicators:
        if indicator not in indicator_fields:
            continue
        
        # Формируем запрос агрегации для конкретного индикатора
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
                    "avg_value": {"$avg": indicator_fields[indicator]},
                    "min_value": {"$min": indicator_fields[indicator]},
                    "max_value": {"$max": indicator_fields[indicator]},
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
                    "avg_value": 1,
                    "min_value": 1,
                    "max_value": 1,
                    "count": 1,
                    "date": 1
                }
            }
        ]
        
        # Выполняем агрегацию
        indicator_results = await db[STATE_SNAPSHOTS_COLLECTION].aggregate(pipeline).to_list(length=limit)
        results[indicator] = indicator_results
    
    return results


async def get_needs_satisfaction_trends(
    user_id: str,
    need_ids: Optional[List[str]] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    interval: str = "day",  # "day", "week", "month"
    limit: int = 30  # Ограничение на количество точек данных
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Получает тренды удовлетворенности потребностей пользователя.
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
    
    # Базовый запрос
    match_query = {
        "user_id": user_id,
        "timestamp": {
            "$gte": start_date,
            "$lte": end_date
        }
    }
    
    # Если переданы конкретные need_ids, анализируем только их
    if need_ids:
        # Формируем агрегационный пайплайн для анализа по конкретным потребностям
        results = {}
        
        for need_id in need_ids:
            pipeline = [
                {"$match": match_query},
                {"$unwind": "$needs"},
                {"$match": {"needs.need_id": need_id}},
                {
                    "$group": {
                        "_id": date_trunc,
                        "avg_satisfaction": {"$avg": "$needs.satisfaction_level"},
                        "min_satisfaction": {"$min": "$needs.satisfaction_level"},
                        "max_satisfaction": {"$max": "$needs.satisfaction_level"},
                        "count": {"$sum": 1},
                        "date": {"$first": "$timestamp"}
                    }
                },
                {"$sort": {"date": 1}},
                {
                    "$project": {
                        "_id": 0,
                        "period": "$_id",
                        "avg_satisfaction": 1,
                        "min_satisfaction": 1,
                        "max_satisfaction": 1,
                        "count": 1,
                        "date": 1
                    }
                }
            ]
            
            need_results = await db[STATE_SNAPSHOTS_COLLECTION].aggregate(pipeline).to_list(length=limit)
            results[need_id] = need_results
        
        return results
    else:
        # Если need_ids не указаны, анализируем все потребности пользователя
        # Сначала получим список всех потребностей, которые есть в снимках состояния
        needs_pipeline = [
            {"$match": match_query},
            {"$unwind": "$needs"},
            {"$group": {
                "_id": "$needs.need_id"
            }}
        ]
        
        needs_results = await db[STATE_SNAPSHOTS_COLLECTION].aggregate(needs_pipeline).to_list(length=100)
        all_need_ids = [result["_id"] for result in needs_results]
        
        # Теперь получаем тренды для каждой потребности
        results = {}
        
        for need_id in all_need_ids:
            pipeline = [
                {"$match": match_query},
                {"$unwind": "$needs"},
                {"$match": {"needs.need_id": need_id}},
                {
                    "$group": {
                        "_id": date_trunc,
                        "avg_satisfaction": {"$avg": "$needs.satisfaction_level"},
                        "min_satisfaction": {"$min": "$needs.satisfaction_level"},
                        "max_satisfaction": {"$max": "$needs.satisfaction_level"},
                        "count": {"$sum": 1},
                        "date": {"$first": "$timestamp"}
                    }
                },
                {"$sort": {"date": 1}},
                {
                    "$project": {
                        "_id": 0,
                        "period": "$_id",
                        "avg_satisfaction": 1,
                        "min_satisfaction": 1,
                        "max_satisfaction": 1,
                        "count": 1,
                        "date": 1
                    }
                }
            ]
            
            need_results = await db[STATE_SNAPSHOTS_COLLECTION].aggregate(pipeline).to_list(length=limit)
            results[need_id] = need_results
        
        return results


async def get_context_factors_analysis(
    user_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Анализ влияния контекстных факторов на состояние пользователя.
    """
    db = await get_mongodb()
    
    # Определяем даты
    if end_date is None:
        end_date = datetime.utcnow()
    
    if start_date is None:
        start_date = end_date - timedelta(days=90)  # Анализируем за последние 90 дней
    
    # Базовый запрос
    match_query = {
        "user_id": user_id,
        "timestamp": {
            "$gte": start_date,
            "$lte": end_date
        },
        "context_factors": {"$exists": True, "$ne": []}
    }
    
    # Разворачиваем массив context_factors и анализируем влияние каждого фактора
    pipeline = [
        {"$match": match_query},
        {"$unwind": "$context_factors"},
        {
            "$group": {
                "_id": "$context_factors",
                "count": {"$sum": 1},
                "avg_mood": {"$avg": "$mood.score"},
                "avg_energy": {"$avg": "$energy.level"},
                "avg_stress": {"$avg": "$stress.level"},
                "snapshots": {"$push": {"_id": "$_id", "timestamp": "$timestamp"}}
            }
        },
        {"$sort": {"count": -1}},
        {
            "$project": {
                "_id": 0,
                "factor": "$_id",
                "count": 1,
                "avg_mood": 1,
                "avg_energy": 1,
                "avg_stress": 1,
                "snapshot_count": {"$size": "$snapshots"}
            }
        }
    ]
    
    factors_analysis = await db[STATE_SNAPSHOTS_COLLECTION].aggregate(pipeline).to_list(length=50)
    
    # Дополнительно рассчитаем базовые средние значения для сравнения
    base_pipeline = [
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
                "_id": None,
                "count": {"$sum": 1},
                "avg_mood": {"$avg": "$mood.score"},
                "avg_energy": {"$avg": "$energy.level"},
                "avg_stress": {"$avg": "$stress.level"}
            }
        },
        {
            "$project": {
                "_id": 0,
                "count": 1,
                "avg_mood": 1,
                "avg_energy": 1,
                "avg_stress": 1
            }
        }
    ]
    
    base_stats_results = await db[STATE_SNAPSHOTS_COLLECTION].aggregate(base_pipeline).to_list(length=1)
    base_stats = base_stats_results[0] if base_stats_results else {
        "count": 0,
        "avg_mood": None,
        "avg_energy": None,
        "avg_stress": None
    }
    
    return {
        "period": {
            "start_date": start_date,
            "end_date": end_date
        },
        "base_statistics": base_stats,
        "factors_analysis": factors_analysis
    }