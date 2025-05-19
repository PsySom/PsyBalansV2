"""
Модуль для настройки индексов MongoDB.

Данный модуль содержит функции для создания и проверки индексов в коллекциях MongoDB,
что позволяет оптимизировать запросы и повысить производительность базы данных.
"""
from typing import Dict, List, Any, Tuple
import logging
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.errors import OperationFailure
from pymongo import ASCENDING, DESCENDING, TEXT, IndexModel

logger = logging.getLogger(__name__)


async def create_index_if_not_exists(collection, index_spec: Dict[str, int], index_name: str = None,
                              unique: bool = False, sparse: bool = False, background: bool = True,
                              **kwargs) -> bool:
    """
    Создает индекс в коллекции, если он еще не существует.
    
    Args:
        collection: Объект коллекции MongoDB
        index_spec: Спецификация индекса (поля и порядок)
        index_name: Пользовательское имя индекса (опционально)
        unique: Должен ли индекс быть уникальным
        sparse: Должен ли индекс быть разреженным (игнорировать документы с отсутствующими полями)
        background: Создавать ли индекс в фоновом режиме
        **kwargs: Дополнительные параметры для создания индекса
        
    Returns:
        bool: True, если индекс создан или уже существовал, False в случае ошибки
    """
    options = {
        "name": index_name,
        "unique": unique, 
        "sparse": sparse,
        "background": background
    }
    options.update(kwargs)
    
    # Очищаем None значения из опций
    options = {k: v for k, v in options.items() if v is not None}
    
    try:
        # Проверяем, существует ли индекс с таким именем
        existing_indexes = await collection.index_information()
        
        if index_name and index_name in existing_indexes:
            logger.info(f"Индекс '{index_name}' уже существует в коллекции {collection.name}")
            return True
        
        # Создаем индекс
        await collection.create_index(list(index_spec.items()), **options)
        logger.info(f"Создан индекс '{index_name or 'unnamed'}' в коллекции {collection.name}")
        return True
    except OperationFailure as e:
        logger.error(f"Не удалось создать индекс в коллекции {collection.name}: {str(e)}")
        return False


async def create_text_index(collection, fields: List[Tuple[str, int]], 
                     default_language: str = "russian", index_name: str = None,
                     background: bool = True) -> bool:
    """
    Создает полнотекстовый индекс для заданных полей.
    
    Args:
        collection: Объект коллекции MongoDB
        fields: Список кортежей (поле, вес)
        default_language: Язык для полнотекстового индекса
        index_name: Пользовательское имя индекса
        background: Создавать ли индекс в фоновом режиме
        
    Returns:
        bool: True, если индекс создан или уже существовал, False в случае ошибки
    """
    try:
        # Преобразовываем список кортежей в словарь текстовых весов
        text_weights = {}
        indexed_fields = {}
        for field, weight in fields:
            text_weights[field] = weight
            indexed_fields[field] = TEXT
        
        # Проверяем, существует ли уже текстовый индекс
        existing_indexes = await collection.index_information()
        has_text_index = any('_fts' in index.get('key', []) for index in existing_indexes.values())
        
        if has_text_index:
            logger.info(f"Полнотекстовый индекс уже существует в коллекции {collection.name}")
            return True
        
        # Создаем текстовый индекс
        options = {
            "name": index_name or f"{collection.name}_text_index",
            "weights": text_weights,
            "default_language": default_language,
            "background": background
        }
        
        await collection.create_index(list(indexed_fields.items()), **options)
        logger.info(f"Создан полнотекстовый индекс в коллекции {collection.name}")
        return True
    except OperationFailure as e:
        logger.error(f"Не удалось создать полнотекстовый индекс в коллекции {collection.name}: {str(e)}")
        return False


async def create_compound_index(collection, fields: List[Tuple[str, int]], 
                         index_name: str = None, unique: bool = False, 
                         sparse: bool = False, partial_filter: Dict = None,
                         background: bool = True) -> bool:
    """
    Создает составной индекс для нескольких полей.
    
    Args:
        collection: Объект коллекции MongoDB
        fields: Список кортежей (поле, направление)
        index_name: Пользовательское имя индекса
        unique: Должен ли индекс быть уникальным
        sparse: Должен ли индекс быть разреженным
        partial_filter: Фильтр для частичного индекса
        background: Создавать ли индекс в фоновом режиме
        
    Returns:
        bool: True, если индекс создан или уже существовал, False в случае ошибки
    """
    options = {
        "name": index_name,
        "unique": unique,
        "sparse": sparse,
        "background": background
    }
    
    if partial_filter:
        options["partialFilterExpression"] = partial_filter
    
    try:
        # Проверяем, существует ли индекс с таким именем
        existing_indexes = await collection.index_information()
        
        if index_name and index_name in existing_indexes:
            logger.info(f"Индекс '{index_name}' уже существует в коллекции {collection.name}")
            return True
        
        # Создаем составной индекс
        await collection.create_index(fields, **options)
        logger.info(f"Создан составной индекс '{index_name or 'unnamed'}' в коллекции {collection.name}")
        return True
    except OperationFailure as e:
        logger.error(f"Не удалось создать составной индекс в коллекции {collection.name}: {str(e)}")
        return False


async def create_mood_entries_indexes(db) -> None:
    """
    Создает индексы для коллекции mood_entries.
    
    Args:
        db: Объект базы данных MongoDB
    """
    collection = db.mood_entries
    
    # Одиночные индексы
    await create_index_if_not_exists(collection, {"user_id": ASCENDING}, "ix_mood_entries_user_id")
    await create_index_if_not_exists(collection, {"timestamp": DESCENDING}, "ix_mood_entries_timestamp")
    await create_index_if_not_exists(collection, {"mood_score": ASCENDING}, "ix_mood_entries_mood_score")
    
    # Составные индексы для типичных запросов
    await create_compound_index(
        collection,
        [("user_id", ASCENDING), ("timestamp", DESCENDING)],
        index_name="ix_mood_entries_user_timestamp"
    )
    
    await create_compound_index(
        collection,
        [("user_id", ASCENDING), ("mood_score", ASCENDING), ("timestamp", DESCENDING)],
        index_name="ix_mood_entries_user_mood_time"
    )
    
    # Текстовый индекс для полнотекстового поиска
    await create_text_index(
        collection,
        [("context", 2), ("notes", 1)],
        index_name="ix_mood_entries_text_search"
    )
    
    logger.info("Индексы для коллекции mood_entries настроены успешно")


async def create_thought_entries_indexes(db) -> None:
    """
    Создает индексы для коллекции thought_entries.
    
    Args:
        db: Объект базы данных MongoDB
    """
    collection = db.thought_entries
    
    # Одиночные индексы
    await create_index_if_not_exists(collection, {"user_id": ASCENDING}, "ix_thought_entries_user_id")
    await create_index_if_not_exists(collection, {"timestamp": DESCENDING}, "ix_thought_entries_timestamp")
    await create_index_if_not_exists(collection, {"automatic_thoughts.cognitive_distortions": ASCENDING}, 
                              "ix_thought_entries_cognitive_distortions")
    
    # Составные индексы для типичных запросов
    await create_compound_index(
        collection,
        [("user_id", ASCENDING), ("timestamp", DESCENDING)],
        index_name="ix_thought_entries_user_timestamp"
    )
    
    # Индекс для поиска по когнитивным искажениям конкретного пользователя
    await create_compound_index(
        collection,
        [("user_id", ASCENDING), ("automatic_thoughts.cognitive_distortions", ASCENDING)],
        index_name="ix_thought_entries_user_distortions"
    )
    
    # Текстовый индекс для полнотекстового поиска
    await create_text_index(
        collection,
        [("situation", 3), ("automatic_thoughts.content", 5), ("balanced_thought", 4), ("action_plan", 2)],
        index_name="ix_thought_entries_text_search"
    )
    
    logger.info("Индексы для коллекции thought_entries настроены успешно")


async def create_activity_evaluations_indexes(db) -> None:
    """
    Создает индексы для коллекции activity_evaluations.
    
    Args:
        db: Объект базы данных MongoDB
    """
    collection = db.activity_evaluations
    
    # Одиночные индексы
    await create_index_if_not_exists(collection, {"user_id": ASCENDING}, "ix_activity_evaluations_user_id")
    await create_index_if_not_exists(collection, {"activity_id": ASCENDING}, "ix_activity_evaluations_activity_id")
    await create_index_if_not_exists(collection, {"timestamp": DESCENDING}, "ix_activity_evaluations_timestamp")
    await create_index_if_not_exists(collection, {"satisfaction_result": ASCENDING}, "ix_activity_evaluations_satisfaction_result")
    await create_index_if_not_exists(collection, {"satisfaction_process": ASCENDING}, "ix_activity_evaluations_satisfaction_process")
    
    # Составные индексы для типичных запросов
    await create_compound_index(
        collection,
        [("user_id", ASCENDING), ("activity_id", ASCENDING), ("timestamp", DESCENDING)],
        index_name="ix_activity_evaluations_user_activity_time"
    )
    
    # Индекс для поиска активностей с высоким уровнем удовлетворенности
    await create_compound_index(
        collection,
        [("user_id", ASCENDING), ("satisfaction_result", DESCENDING)],
        index_name="ix_activity_evaluations_user_high_satisfaction",
        partial_filter={"satisfaction_result": {"$gte": 7}}
    )
    
    # Индекс для поиска активностей с низким уровнем удовлетворенности
    await create_compound_index(
        collection,
        [("user_id", ASCENDING), ("satisfaction_result", ASCENDING)],
        index_name="ix_activity_evaluations_user_low_satisfaction",
        partial_filter={"satisfaction_result": {"$lt": 4}}
    )
    
    # Текстовый индекс для полнотекстового поиска
    await create_text_index(
        collection,
        [("notes", 1)],
        index_name="ix_activity_evaluations_text_search"
    )
    
    logger.info("Индексы для коллекции activity_evaluations настроены успешно")


async def create_state_snapshots_indexes(db) -> None:
    """
    Создает индексы для коллекции state_snapshots.
    
    Args:
        db: Объект базы данных MongoDB
    """
    collection = db.state_snapshots
    
    # Одиночные индексы
    await create_index_if_not_exists(collection, {"user_id": ASCENDING}, "ix_state_snapshots_user_id")
    await create_index_if_not_exists(collection, {"timestamp": DESCENDING}, "ix_state_snapshots_timestamp")
    await create_index_if_not_exists(collection, {"snapshot_type": ASCENDING}, "ix_state_snapshots_type")
    
    # Составные индексы для типичных запросов
    await create_compound_index(
        collection,
        [("user_id", ASCENDING), ("timestamp", DESCENDING)],
        index_name="ix_state_snapshots_user_timestamp"
    )
    
    await create_compound_index(
        collection,
        [("user_id", ASCENDING), ("snapshot_type", ASCENDING), ("timestamp", DESCENDING)],
        index_name="ix_state_snapshots_user_type_time"
    )
    
    # Индексы для поиска по показателям
    await create_index_if_not_exists(collection, {"mood.score": ASCENDING}, "ix_state_snapshots_mood_score")
    await create_index_if_not_exists(collection, {"energy.level": ASCENDING}, "ix_state_snapshots_energy_level")
    await create_index_if_not_exists(collection, {"stress.level": ASCENDING}, "ix_state_snapshots_stress_level")
    
    # Текстовый индекс для полнотекстового поиска
    await create_text_index(
        collection,
        [("mood.notes", 2), ("energy.notes", 2), ("stress.notes", 2), ("needs.notes", 1)],
        index_name="ix_state_snapshots_text_search"
    )
    
    logger.info("Индексы для коллекции state_snapshots настроены успешно")


async def create_recommendations_indexes(db) -> None:
    """
    Создает индексы для коллекции recommendations.
    
    Args:
        db: Объект базы данных MongoDB
    """
    collection = db.recommendations
    
    # Одиночные индексы
    await create_index_if_not_exists(collection, {"user_id": ASCENDING}, "ix_recommendations_user_id")
    await create_index_if_not_exists(collection, {"recommendation_type": ASCENDING}, "ix_recommendations_type")
    await create_index_if_not_exists(collection, {"user_response.status": ASCENDING}, "ix_recommendations_status")
    await create_index_if_not_exists(collection, {"created_at": DESCENDING}, "ix_recommendations_created_at")
    
    # Составные индексы для типичных запросов
    await create_compound_index(
        collection,
        [("user_id", ASCENDING), ("recommendation_type", ASCENDING), ("created_at", DESCENDING)],
        index_name="ix_recommendations_user_type_time"
    )
    
    await create_compound_index(
        collection,
        [("user_id", ASCENDING), ("user_response.status", ASCENDING), ("created_at", DESCENDING)],
        index_name="ix_recommendations_user_status_time"
    )
    
    # Индекс для поиска принятых рекомендаций
    await create_compound_index(
        collection,
        [("user_id", ASCENDING), ("user_response.status", ASCENDING)],
        index_name="ix_recommendations_accepted",
        partial_filter={"user_response.status": "accepted"}
    )
    
    # Индекс для поиска отклоненных рекомендаций
    await create_compound_index(
        collection,
        [("user_id", ASCENDING), ("user_response.status", ASCENDING)],
        index_name="ix_recommendations_declined",
        partial_filter={"user_response.status": "declined"}
    )
    
    # Текстовый индекс для полнотекстового поиска
    await create_text_index(
        collection,
        [("recommended_items.explanation", 3), ("user_response.user_feedback", 2)],
        index_name="ix_recommendations_text_search"
    )
    
    logger.info("Индексы для коллекции recommendations настроены успешно")


async def setup_mongodb_indexes(db) -> None:
    """
    Настраивает все необходимые индексы в базе данных MongoDB.
    
    Args:
        db: Объект базы данных MongoDB
    """
    logger.info("Начинаем настройку индексов MongoDB...")
    
    # Выполняем настройку индексов для каждой коллекции
    await create_mood_entries_indexes(db)
    await create_thought_entries_indexes(db)
    await create_activity_evaluations_indexes(db)
    await create_state_snapshots_indexes(db)
    await create_recommendations_indexes(db)
    
    logger.info("Все индексы MongoDB успешно настроены")