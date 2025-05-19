"""
Унифицированный репозиторий для работы со всеми типами дневников.
Обеспечивает маршрутизацию, поиск, агрегацию и анализ данных из разных дневников.
"""
from typing import List, Dict, Any, Optional, Union, Tuple, Literal
from datetime import datetime, timedelta
from enum import Enum
import json
import csv
import io
import logging
from bson import ObjectId
from pymongo import ReturnDocument

from app.core.database.mongodb import get_mongodb
from app.mongodb.recommendations_diary_repository import DiaryEntriesRepository
from app.mongodb.mood_thought_repository import (
    get_mood_entry, get_user_mood_entries, create_mood_entry, update_mood_entry, delete_mood_entry,
    get_thought_entry, get_user_thought_entries, create_thought_entry, update_thought_entry, delete_thought_entry,
    MOOD_ENTRIES_COLLECTION, THOUGHT_ENTRIES_COLLECTION
)
from app.mongodb.activity_evaluation_repository import (
    create_activity_evaluation, get_activity_evaluation,
    get_user_activity_evaluations, update_activity_evaluation, delete_activity_evaluation
)

logger = logging.getLogger(__name__)


class DiaryType(str, Enum):
    """Типы дневников в системе."""
    INTEGRATIVE = "integrative"  # Интегративный дневник
    MOOD = "mood"                # Дневник настроения
    THOUGHT = "thought"          # Дневник мыслей
    ACTIVITY = "activity"        # Дневник активностей


class DiaryFormat(str, Enum):
    """Форматы экспорта дневников."""
    JSON = "json"
    CSV = "csv"
    TXT = "txt"


class DiaryRepository:
    """
    Унифицированный репозиторий для работы со всеми типами дневников.
    Обеспечивает маршрутизацию запросов к соответствующим специализированным репозиториям
    и предоставляет методы для общих операций над дневниками.
    """
    
    def __init__(self, db=None):
        """
        Инициализация репозитория с опциональным соединением к БД.
        
        Args:
            db: Объект соединения с MongoDB или None для отложенного подключения
        """
        self.db = db
        self.integrative_diary_repo = DiaryEntriesRepository(db)
    
    async def get_db(self):
        """
        Получение подключения к базе данных MongoDB.
        
        Returns:
            Соединение с MongoDB
        """
        if self.db is None:
            self.db = await get_mongodb()
        return self.db
    
    # -------------------------------------------------------------------------
    # Методы для создания записей в дневниках разных типов
    # -------------------------------------------------------------------------
    
    async def create_entry(
        self, 
        diary_type: DiaryType, 
        entry_data: Dict[str, Any]
    ) -> str:
        """
        Создает новую запись в соответствующем типе дневника.
        
        Args:
            diary_type: Тип дневника
            entry_data: Данные для создания записи
            
        Returns:
            ID созданной записи
            
        Raises:
            ValueError: Если указан неизвестный тип дневника
        """
        if diary_type == DiaryType.INTEGRATIVE:
            return await self.integrative_diary_repo.create_diary_entry(entry_data)
        
        elif diary_type == DiaryType.MOOD:
            # Извлекаем необходимые поля из словаря для дневника настроения
            return await create_mood_entry(
                user_id=entry_data.get("user_id"),
                mood_score=entry_data.get("mood_score"),
                emotions=entry_data.get("emotions", []),
                timestamp=entry_data.get("timestamp"),
                triggers=entry_data.get("triggers"),
                physical_sensations=entry_data.get("physical_sensations"),
                body_areas=entry_data.get("body_areas"),
                context=entry_data.get("context"),
                notes=entry_data.get("notes")
            )
        
        elif diary_type == DiaryType.THOUGHT:
            # Извлекаем необходимые поля из словаря для дневника мыслей
            return await create_thought_entry(
                user_id=entry_data.get("user_id"),
                situation=entry_data.get("situation"),
                automatic_thoughts=entry_data.get("automatic_thoughts", []),
                emotions=entry_data.get("emotions", []),
                timestamp=entry_data.get("timestamp"),
                evidence_for=entry_data.get("evidence_for"),
                evidence_against=entry_data.get("evidence_against"),
                balanced_thought=entry_data.get("balanced_thought"),
                new_belief_level=entry_data.get("new_belief_level"),
                action_plan=entry_data.get("action_plan")
            )
        
        elif diary_type == DiaryType.ACTIVITY:
            # Извлекаем необходимые поля из словаря для дневника активностей
            return await create_activity_evaluation(
                user_id=entry_data.get("user_id"),
                activity_id=entry_data.get("activity_id"),
                rating=entry_data.get("rating"),
                status=entry_data.get("status"),
                mood_before=entry_data.get("mood_before"),
                mood_after=entry_data.get("mood_after"),
                energy_before=entry_data.get("energy_before"),
                energy_after=entry_data.get("energy_after"),
                notes=entry_data.get("notes"),
                difficulty_level=entry_data.get("difficulty_level"),
                timestamp=entry_data.get("timestamp")
            )
        
        else:
            raise ValueError(f"Неизвестный тип дневника: {diary_type}")
    
    # -------------------------------------------------------------------------
    # Методы для получения записей из дневников разных типов
    # -------------------------------------------------------------------------
    
    async def get_entry(self, diary_type: DiaryType, entry_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает запись из соответствующего типа дневника по ID.
        
        Args:
            diary_type: Тип дневника
            entry_id: ID записи
            
        Returns:
            Запись дневника или None, если запись не найдена
            
        Raises:
            ValueError: Если указан неизвестный тип дневника
        """
        if diary_type == DiaryType.INTEGRATIVE:
            return await self.integrative_diary_repo.get_diary_entry(entry_id)
        
        elif diary_type == DiaryType.MOOD:
            return await get_mood_entry(entry_id)
        
        elif diary_type == DiaryType.THOUGHT:
            return await get_thought_entry(entry_id)
        
        elif diary_type == DiaryType.ACTIVITY:
            return await get_activity_evaluation(entry_id)
        
        else:
            raise ValueError(f"Неизвестный тип дневника: {diary_type}")
    
    async def get_user_entries(
        self,
        user_id: str, 
        diary_type: DiaryType,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        skip: int = 0,
        sort_order: int = -1,
        entry_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Получает записи пользователя из соответствующего типа дневника.
        
        Args:
            user_id: ID пользователя
            diary_type: Тип дневника
            start_date: Начальная дата для фильтрации (включительно)
            end_date: Конечная дата для фильтрации (включительно)
            limit: Максимальное количество записей
            skip: Количество записей для пропуска (пагинация)
            sort_order: Порядок сортировки (1 - по возрастанию даты, -1 - по убыванию)
            entry_type: Тип записи для фильтрации (только для интегративного дневника)
            
        Returns:
            Список записей дневника
            
        Raises:
            ValueError: Если указан неизвестный тип дневника
        """
        if diary_type == DiaryType.INTEGRATIVE:
            return await self.integrative_diary_repo.get_user_diary_entries(
                user_id=user_id, 
                limit=limit, 
                skip=skip,
                start_date=start_date,
                end_date=end_date,
                entry_type=entry_type
            )
        
        elif diary_type == DiaryType.MOOD:
            return await get_user_mood_entries(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                skip=skip,
                sort_order=sort_order
            )
        
        elif diary_type == DiaryType.THOUGHT:
            return await get_user_thought_entries(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                skip=skip,
                sort_order=sort_order
            )
        
        elif diary_type == DiaryType.ACTIVITY:
            return await get_user_activity_evaluations(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                skip=skip
            )
        
        else:
            raise ValueError(f"Неизвестный тип дневника: {diary_type}")
    
    # -------------------------------------------------------------------------
    # Методы для обновления и удаления записей
    # -------------------------------------------------------------------------
    
    async def update_entry(
        self, 
        diary_type: DiaryType, 
        entry_id: str, 
        updates: Dict[str, Any]
    ) -> Union[Dict[str, Any], bool]:
        """
        Обновляет запись в соответствующем типе дневника.
        
        Args:
            diary_type: Тип дневника
            entry_id: ID записи
            updates: Данные для обновления
            
        Returns:
            Обновленная запись или True/False в зависимости от типа дневника
            
        Raises:
            ValueError: Если указан неизвестный тип дневника
        """
        if diary_type == DiaryType.INTEGRATIVE:
            return await self.integrative_diary_repo.update_diary_entry(entry_id, updates)
        
        elif diary_type == DiaryType.MOOD:
            return await update_mood_entry(entry_id, updates)
        
        elif diary_type == DiaryType.THOUGHT:
            return await update_thought_entry(entry_id, updates)
        
        elif diary_type == DiaryType.ACTIVITY:
            return await update_activity_evaluation(entry_id, updates)
        
        else:
            raise ValueError(f"Неизвестный тип дневника: {diary_type}")
    
    async def delete_entry(self, diary_type: DiaryType, entry_id: str) -> bool:
        """
        Удаляет запись из соответствующего типа дневника.
        
        Args:
            diary_type: Тип дневника
            entry_id: ID записи
            
        Returns:
            True, если запись успешно удалена, иначе False
            
        Raises:
            ValueError: Если указан неизвестный тип дневника
        """
        if diary_type == DiaryType.INTEGRATIVE:
            return await self.integrative_diary_repo.delete_diary_entry(entry_id)
        
        elif diary_type == DiaryType.MOOD:
            return await delete_mood_entry(entry_id)
        
        elif diary_type == DiaryType.THOUGHT:
            return await delete_thought_entry(entry_id)
        
        elif diary_type == DiaryType.ACTIVITY:
            return await delete_activity_evaluation(entry_id)
        
        else:
            raise ValueError(f"Неизвестный тип дневника: {diary_type}")
    
    # -------------------------------------------------------------------------
    # Методы для поиска и агрегации данных по всем дневникам
    # -------------------------------------------------------------------------
    
    async def search_across_diaries(
        self, 
        user_id: str,
        query: str,
        diary_types: Optional[List[DiaryType]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Поиск по всем типам дневников.
        
        Args:
            user_id: ID пользователя
            query: Поисковый запрос
            diary_types: Список типов дневников для поиска (если None, то ищет по всем типам)
            start_date: Начальная дата для фильтрации
            end_date: Конечная дата для фильтрации
            limit: Максимальное количество записей для каждого типа дневника
            
        Returns:
            Словарь с результатами поиска по каждому типу дневника
        """
        db = await self.get_db()
        
        # Определяем типы дневников для поиска
        if diary_types is None:
            diary_types = list(DiaryType)
        
        # Формируем базовый запрос
        base_query = {
            "user_id": user_id,
            "$text": {"$search": query}
        }
        
        # Добавляем фильтрацию по датам
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = start_date
            if end_date:
                date_filter["$lte"] = end_date
            base_query["timestamp"] = date_filter
        
        # Результаты поиска по типам дневников
        results = {}
        
        # Поиск в интегративном дневнике
        if DiaryType.INTEGRATIVE in diary_types:
            # Подготавливаем запрос для поиска в интегративном дневнике
            integrative_query = base_query.copy()
            
            # Корректируем запрос для поиска в полях диалога
            integrative_query["$or"] = [
                {"$text": {"$search": query}},
                {"conversation.content": {"$regex": query, "$options": "i"}}
            ]
            del integrative_query["$text"]
            
            # Выполняем поиск
            integrative_cursor = db["diary_entries"].find(integrative_query).limit(limit)
            integrative_results = await integrative_cursor.to_list(length=limit)
            
            # Обрабатываем результаты
            for result in integrative_results:
                result["_id"] = str(result["_id"])
            
            results[DiaryType.INTEGRATIVE] = integrative_results
        
        # Поиск в дневнике настроения
        if DiaryType.MOOD in diary_types:
            # Выполняем поиск по полям, включая notes, context, triggers
            mood_query = {
                "user_id": user_id,
                "$or": [
                    {"notes": {"$regex": query, "$options": "i"}},
                    {"context": {"$regex": query, "$options": "i"}},
                    {"triggers": {"$regex": query, "$options": "i"}}
                ]
            }
            
            # Добавляем фильтрацию по датам
            if start_date or end_date:
                date_filter = {}
                if start_date:
                    date_filter["$gte"] = start_date
                if end_date:
                    date_filter["$lte"] = end_date
                mood_query["timestamp"] = date_filter
            
            # Выполняем поиск
            mood_cursor = db[MOOD_ENTRIES_COLLECTION].find(mood_query).limit(limit)
            mood_results = await mood_cursor.to_list(length=limit)
            
            # Обрабатываем результаты
            for result in mood_results:
                result["_id"] = str(result["_id"])
            
            results[DiaryType.MOOD] = mood_results
        
        # Поиск в дневнике мыслей
        if DiaryType.THOUGHT in diary_types:
            # Выполняем поиск по полям, включая situation, balanced_thought, action_plan
            thought_query = {
                "user_id": user_id,
                "$or": [
                    {"situation": {"$regex": query, "$options": "i"}},
                    {"balanced_thought": {"$regex": query, "$options": "i"}},
                    {"action_plan": {"$regex": query, "$options": "i"}},
                    {"automatic_thoughts.content": {"$regex": query, "$options": "i"}}
                ]
            }
            
            # Добавляем фильтрацию по датам
            if start_date or end_date:
                date_filter = {}
                if start_date:
                    date_filter["$gte"] = start_date
                if end_date:
                    date_filter["$lte"] = end_date
                thought_query["timestamp"] = date_filter
            
            # Выполняем поиск
            thought_cursor = db[THOUGHT_ENTRIES_COLLECTION].find(thought_query).limit(limit)
            thought_results = await thought_cursor.to_list(length=limit)
            
            # Обрабатываем результаты
            for result in thought_results:
                result["_id"] = str(result["_id"])
            
            results[DiaryType.THOUGHT] = thought_results
        
        # Поиск в дневнике активностей
        if DiaryType.ACTIVITY in diary_types:
            # Выполняем поиск по полям, включая notes
            activity_query = {
                "user_id": user_id,
                "notes": {"$regex": query, "$options": "i"}
            }
            
            # Добавляем фильтрацию по датам
            if start_date or end_date:
                date_filter = {}
                if start_date:
                    date_filter["$gte"] = start_date
                if end_date:
                    date_filter["$lte"] = end_date
                activity_query["timestamp"] = date_filter
            
            # Выполняем поиск
            activity_cursor = db["activity_evaluations"].find(activity_query).limit(limit)
            activity_results = await activity_cursor.to_list(length=limit)
            
            # Обрабатываем результаты
            for result in activity_results:
                result["_id"] = str(result["_id"])
            
            results[DiaryType.ACTIVITY] = activity_results
        
        return results
    
    async def get_entries_by_date_range(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        diary_types: Optional[List[DiaryType]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Получает записи из всех дневников за указанный период.
        
        Args:
            user_id: ID пользователя
            start_date: Начальная дата
            end_date: Конечная дата
            diary_types: Список типов дневников (если None, то все типы)
            
        Returns:
            Словарь с записями по каждому типу дневника
        """
        if diary_types is None:
            diary_types = list(DiaryType)
        
        results = {}
        for diary_type in diary_types:
            entries = await self.get_user_entries(
                user_id=user_id,
                diary_type=diary_type,
                start_date=start_date,
                end_date=end_date,
                limit=1000  # Увеличенный лимит для полного охвата периода
            )
            results[diary_type] = entries
        
        return results
    
    # -------------------------------------------------------------------------
    # Методы для анализа данных из разных дневников
    # -------------------------------------------------------------------------
    
    async def aggregate_mood_data(
        self,
        user_id: str,
        period: str = "week",  # "day", "week", "month", "year", "all"
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Агрегирует данные о настроении из разных дневников.
        
        Args:
            user_id: ID пользователя
            period: Период агрегации
            end_date: Конечная дата периода
            
        Returns:
            Агрегированные данные о настроении
        """
        db = await self.get_db()
        
        # Определяем даты
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
        
        # Запрос для агрегации данных из дневника настроения
        mood_pipeline = [
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
                    "avg_mood": {"$avg": "$mood_score"},
                    "min_mood": {"$min": "$mood_score"},
                    "max_mood": {"$max": "$mood_score"},
                    "count": {"$sum": 1}
                }
            }
        ]
        
        # Запрос для агрегации данных из дневника активностей
        activity_pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "timestamp": {
                        "$gte": start_date,
                        "$lte": end_date
                    },
                    "mood_before": {"$exists": True},
                    "mood_after": {"$exists": True}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "avg_mood_before": {"$avg": "$mood_before"},
                    "avg_mood_after": {"$avg": "$mood_after"},
                    "avg_mood_change": {"$avg": {"$subtract": ["$mood_after", "$mood_before"]}},
                    "count": {"$sum": 1}
                }
            }
        ]
        
        # Запрос для агрегации данных из интегративного дневника
        integrative_pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "timestamp": {
                        "$gte": start_date,
                        "$lte": end_date
                    },
                    "extracted_data.mood": {"$exists": True}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "avg_mood": {"$avg": "$extracted_data.mood"},
                    "count": {"$sum": 1}
                }
            }
        ]
        
        # Выполняем агрегацию по каждому источнику данных
        mood_result = await db[MOOD_ENTRIES_COLLECTION].aggregate(mood_pipeline).to_list(length=1)
        activity_result = await db["activity_evaluations"].aggregate(activity_pipeline).to_list(length=1)
        integrative_result = await db["diary_entries"].aggregate(integrative_pipeline).to_list(length=1)
        
        # Объединяем результаты
        mood_stats = mood_result[0] if mood_result else {"avg_mood": None, "min_mood": None, "max_mood": None, "count": 0}
        activity_stats = activity_result[0] if activity_result else {"avg_mood_before": None, "avg_mood_after": None, "avg_mood_change": None, "count": 0}
        integrative_stats = integrative_result[0] if integrative_result else {"avg_mood": None, "count": 0}
        
        combined_stats = {
            "period": period,
            "start_date": start_date,
            "end_date": end_date,
            "mood_diary": {
                "avg_mood": mood_stats["avg_mood"],
                "min_mood": mood_stats["min_mood"],
                "max_mood": mood_stats["max_mood"],
                "entries_count": mood_stats["count"]
            },
            "activity_diary": {
                "avg_mood_before": activity_stats["avg_mood_before"],
                "avg_mood_after": activity_stats["avg_mood_after"],
                "avg_mood_change": activity_stats["avg_mood_change"],
                "entries_count": activity_stats["count"]
            },
            "integrative_diary": {
                "avg_mood": integrative_stats["avg_mood"],
                "entries_count": integrative_stats["count"]
            }
        }
        
        # Рассчитываем общую среднюю оценку настроения
        total_weighted_mood = 0
        total_count = 0
        
        if mood_stats["avg_mood"] is not None:
            total_weighted_mood += mood_stats["avg_mood"] * mood_stats["count"]
            total_count += mood_stats["count"]
        
        if integrative_stats["avg_mood"] is not None:
            total_weighted_mood += integrative_stats["avg_mood"] * integrative_stats["count"]
            total_count += integrative_stats["count"]
        
        if total_count > 0:
            combined_stats["overall_avg_mood"] = total_weighted_mood / total_count
        else:
            combined_stats["overall_avg_mood"] = None
        
        return combined_stats
    
    async def analyze_correlations(
        self,
        user_id: str,
        period: str = "month",  # "week", "month", "year", "all"
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Анализирует корреляции между данными из разных дневников.
        
        Args:
            user_id: ID пользователя
            period: Период анализа
            end_date: Конечная дата периода
            
        Returns:
            Результаты анализа корреляций
        """
        db = await self.get_db()
        
        # Определяем даты
        if end_date is None:
            end_date = datetime.utcnow()
        
        if period == "week":
            start_date = end_date - timedelta(days=7)
        elif period == "month":
            start_date = end_date - timedelta(days=30)
        elif period == "year":
            start_date = end_date - timedelta(days=365)
        elif period == "all":
            start_date = datetime.min
        else:
            raise ValueError(f"Неподдерживаемый период: {period}")
        
        # Получаем данные из разных дневников
        mood_entries = await self.get_user_entries(
            user_id=user_id,
            diary_type=DiaryType.MOOD,
            start_date=start_date,
            end_date=end_date,
            limit=1000
        )
        
        thought_entries = await self.get_user_entries(
            user_id=user_id,
            diary_type=DiaryType.THOUGHT,
            start_date=start_date,
            end_date=end_date,
            limit=1000
        )
        
        activity_entries = await self.get_user_entries(
            user_id=user_id,
            diary_type=DiaryType.ACTIVITY,
            start_date=start_date,
            end_date=end_date,
            limit=1000
        )
        
        # Анализируем корреляцию: активности и настроение
        activity_mood_correlation = await self._analyze_activity_mood_correlation(activity_entries)
        
        # Анализируем корреляцию: типы мыслей и настроение
        thought_mood_correlation = await self._analyze_thought_mood_correlation(thought_entries, mood_entries)
        
        # Анализируем корреляцию: триггеры и настроение
        trigger_mood_correlation = await self._analyze_trigger_mood_correlation(mood_entries)
        
        # Возвращаем результаты анализа
        return {
            "period": period,
            "start_date": start_date,
            "end_date": end_date,
            "activity_mood_correlation": activity_mood_correlation,
            "thought_mood_correlation": thought_mood_correlation,
            "trigger_mood_correlation": trigger_mood_correlation
        }
    
    async def _analyze_activity_mood_correlation(
        self, 
        activity_entries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Анализирует корреляцию между активностями и изменениями настроения.
        
        Args:
            activity_entries: Записи о выполненных активностях
            
        Returns:
            Результаты анализа корреляции
        """
        if not activity_entries:
            return {
                "activities_with_positive_impact": [],
                "activities_with_negative_impact": [],
                "high_energy_impact": []
            }
        
        # Группируем активности по ID и рассчитываем среднее изменение настроения
        activity_impacts = {}
        
        for entry in activity_entries:
            activity_id = entry.get("activity_id")
            if not activity_id:
                continue
                
            mood_before = entry.get("mood_before")
            mood_after = entry.get("mood_after")
            
            if mood_before is None or mood_after is None:
                continue
                
            mood_change = mood_after - mood_before
            
            energy_before = entry.get("energy_before")
            energy_after = entry.get("energy_after")
            energy_change = None
            if energy_before is not None and energy_after is not None:
                energy_change = energy_after - energy_before
            
            if activity_id not in activity_impacts:
                activity_impacts[activity_id] = {
                    "activity_id": activity_id,
                    "mood_changes": [mood_change],
                    "energy_changes": [] if energy_change is None else [energy_change]
                }
            else:
                activity_impacts[activity_id]["mood_changes"].append(mood_change)
                if energy_change is not None:
                    activity_impacts[activity_id]["energy_changes"].append(energy_change)
        
        # Рассчитываем средние изменения для каждой активности
        for activity_id, data in activity_impacts.items():
            mood_changes = data["mood_changes"]
            data["avg_mood_change"] = sum(mood_changes) / len(mood_changes)
            
            energy_changes = data["energy_changes"]
            if energy_changes:
                data["avg_energy_change"] = sum(energy_changes) / len(energy_changes)
            else:
                data["avg_energy_change"] = None
        
        # Сортируем активности по влиянию на настроение
        sorted_by_mood = sorted(
            activity_impacts.values(),
            key=lambda x: x["avg_mood_change"],
            reverse=True
        )
        
        # Выбираем активности с наибольшим положительным и отрицательным влиянием
        activities_with_positive_impact = [
            {
                "activity_id": a["activity_id"],
                "avg_mood_change": a["avg_mood_change"],
                "count": len(a["mood_changes"])
            }
            for a in sorted_by_mood if a["avg_mood_change"] > 0
        ][:5]
        
        activities_with_negative_impact = [
            {
                "activity_id": a["activity_id"],
                "avg_mood_change": a["avg_mood_change"],
                "count": len(a["mood_changes"])
            }
            for a in sorted_by_mood if a["avg_mood_change"] < 0
        ][-5:]
        
        # Активности с наибольшим влиянием на энергию
        sorted_by_energy = sorted(
            [a for a in activity_impacts.values() if a["avg_energy_change"] is not None],
            key=lambda x: x["avg_energy_change"],
            reverse=True
        )
        
        high_energy_impact = [
            {
                "activity_id": a["activity_id"],
                "avg_energy_change": a["avg_energy_change"],
                "count": len(a["energy_changes"])
            }
            for a in sorted_by_energy if a["avg_energy_change"] > 0
        ][:5]
        
        return {
            "activities_with_positive_impact": activities_with_positive_impact,
            "activities_with_negative_impact": activities_with_negative_impact,
            "high_energy_impact": high_energy_impact
        }
    
    async def _analyze_thought_mood_correlation(
        self, 
        thought_entries: List[Dict[str, Any]], 
        mood_entries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Анализирует корреляцию между типами мыслей и настроением.
        
        Args:
            thought_entries: Записи из дневника мыслей
            mood_entries: Записи из дневника настроения
            
        Returns:
            Результаты анализа корреляции
        """
        if not thought_entries or not mood_entries:
            return {
                "distortions_mood_correlation": [],
                "balanced_thought_impact": None
            }
        
        # Группируем записи настроения по дням для сопоставления с записями мыслей
        mood_by_day = {}
        for entry in mood_entries:
            day = entry["timestamp"].strftime("%Y-%m-%d")
            if day not in mood_by_day:
                mood_by_day[day] = []
            mood_by_day[day].append(entry["mood_score"])
        
        # Рассчитываем среднее настроение за каждый день
        avg_mood_by_day = {
            day: sum(scores) / len(scores)
            for day, scores in mood_by_day.items()
        }
        
        # Анализируем влияние когнитивных искажений
        distortion_mood = {}
        for entry in thought_entries:
            day = entry["timestamp"].strftime("%Y-%m-%d")
            if day not in avg_mood_by_day:
                continue
                
            day_mood = avg_mood_by_day[day]
            
            # Собираем когнитивные искажения из мыслей
            if "automatic_thoughts" in entry:
                for thought in entry["automatic_thoughts"]:
                    if "cognitive_distortions" in thought and thought["cognitive_distortions"]:
                        for distortion in thought["cognitive_distortions"]:
                            if distortion not in distortion_mood:
                                distortion_mood[distortion] = []
                            distortion_mood[distortion].append(day_mood)
        
        # Рассчитываем среднее настроение для каждого типа когнитивных искажений
        distortions_mood_correlation = [
            {
                "distortion": distortion,
                "avg_mood": sum(moods) / len(moods),
                "count": len(moods)
            }
            for distortion, moods in distortion_mood.items()
            if len(moods) >= 3  # минимальное количество наблюдений
        ]
        
        # Сортируем по среднему настроению (от низкого к высокому)
        distortions_mood_correlation.sort(key=lambda x: x["avg_mood"])
        
        # Анализируем влияние сбалансированных мыслей
        balanced_thoughts_impact = None
        entries_with_balanced_thoughts = []
        entries_without_balanced_thoughts = []
        
        for entry in thought_entries:
            day = entry["timestamp"].strftime("%Y-%m-%d")
            if day not in avg_mood_by_day:
                continue
                
            day_mood = avg_mood_by_day[day]
            
            if "balanced_thought" in entry and entry["balanced_thought"]:
                entries_with_balanced_thoughts.append(day_mood)
            else:
                entries_without_balanced_thoughts.append(day_mood)
        
        if entries_with_balanced_thoughts and entries_without_balanced_thoughts:
            avg_with_balanced = sum(entries_with_balanced_thoughts) / len(entries_with_balanced_thoughts)
            avg_without_balanced = sum(entries_without_balanced_thoughts) / len(entries_without_balanced_thoughts)
            
            balanced_thoughts_impact = {
                "avg_mood_with_balanced_thoughts": avg_with_balanced,
                "avg_mood_without_balanced_thoughts": avg_without_balanced,
                "difference": avg_with_balanced - avg_without_balanced,
                "count_with_balanced": len(entries_with_balanced_thoughts),
                "count_without_balanced": len(entries_without_balanced_thoughts)
            }
        
        return {
            "distortions_mood_correlation": distortions_mood_correlation,
            "balanced_thought_impact": balanced_thoughts_impact
        }
    
    async def _analyze_trigger_mood_correlation(
        self, 
        mood_entries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Анализирует корреляцию между триггерами и настроением.
        
        Args:
            mood_entries: Записи из дневника настроения
            
        Returns:
            Результаты анализа корреляции
        """
        if not mood_entries:
            return {
                "triggers_mood_correlation": []
            }
        
        # Группируем записи по триггерам и собираем оценки настроения
        trigger_moods = {}
        
        for entry in mood_entries:
            mood_score = entry.get("mood_score")
            if mood_score is None:
                continue
                
            triggers = entry.get("triggers", [])
            if not triggers:
                continue
                
            for trigger in triggers:
                if trigger not in trigger_moods:
                    trigger_moods[trigger] = []
                trigger_moods[trigger].append(mood_score)
        
        # Рассчитываем среднее настроение для каждого триггера
        triggers_mood_correlation = [
            {
                "trigger": trigger,
                "avg_mood": sum(moods) / len(moods),
                "count": len(moods)
            }
            for trigger, moods in trigger_moods.items()
            if len(moods) >= 3  # минимальное количество наблюдений
        ]
        
        # Сортируем по среднему настроению (от низкого к высокому)
        triggers_mood_correlation.sort(key=lambda x: x["avg_mood"])
        
        return {
            "triggers_mood_correlation": triggers_mood_correlation
        }
    
    # -------------------------------------------------------------------------
    # Методы для экспорта данных дневников
    # -------------------------------------------------------------------------
    
    async def export_diary_data(
        self,
        user_id: str,
        diary_type: DiaryType,
        format: DiaryFormat = DiaryFormat.JSON,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Union[str, bytes]:
        """
        Экспортирует данные дневника в указанном формате.
        
        Args:
            user_id: ID пользователя
            diary_type: Тип дневника
            format: Формат экспорта
            start_date: Начальная дата
            end_date: Конечная дата
            
        Returns:
            Данные дневника в указанном формате
            
        Raises:
            ValueError: Если указан неизвестный тип дневника или формат
        """
        # Получаем записи дневника
        entries = await self.get_user_entries(
            user_id=user_id,
            diary_type=diary_type,
            start_date=start_date,
            end_date=end_date,
            limit=10000  # Большой лимит для экспорта всех данных
        )
        
        # Очищаем служебные поля и форматируем даты
        for entry in entries:
            # Преобразуем даты в строки ISO-формата
            for key in ["timestamp", "created_at", "updated_at"]:
                if key in entry and isinstance(entry[key], datetime):
                    entry[key] = entry[key].isoformat()
        
        # Экспортируем в выбранном формате
        if format == DiaryFormat.JSON:
            return json.dumps(entries, ensure_ascii=False, indent=2)
        
        elif format == DiaryFormat.CSV:
            # Определяем заголовки в зависимости от типа дневника
            if diary_type == DiaryType.MOOD:
                # Заголовки для дневника настроения
                fieldnames = ["_id", "user_id", "timestamp", "mood_score", "context", "notes"]
            elif diary_type == DiaryType.THOUGHT:
                # Заголовки для дневника мыслей
                fieldnames = ["_id", "user_id", "timestamp", "situation", "balanced_thought", "action_plan"]
            elif diary_type == DiaryType.ACTIVITY:
                # Заголовки для дневника активностей
                fieldnames = ["_id", "user_id", "timestamp", "activity_id", "rating", "status", 
                             "mood_before", "mood_after", "energy_before", "energy_after", "notes"]
            elif diary_type == DiaryType.INTEGRATIVE:
                # Заголовки для интегративного дневника
                fieldnames = ["_id", "user_id", "timestamp", "entry_type"]
            else:
                raise ValueError(f"Неизвестный тип дневника: {diary_type}")
            
            # Создаем CSV в памяти
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            
            for entry in entries:
                # Подготавливаем запись для CSV
                row = {field: entry.get(field, "") for field in fieldnames}
                writer.writerow(row)
            
            return output.getvalue()
        
        elif format == DiaryFormat.TXT:
            # Создаем текстовый формат с форматированием
            output = []
            
            if diary_type == DiaryType.MOOD:
                # Форматирование для дневника настроения
                for entry in entries:
                    entry_text = [
                        f"Дата: {entry.get('timestamp', '')}",
                        f"Оценка настроения: {entry.get('mood_score', '')}",
                        f"Контекст: {entry.get('context', '')}",
                        f"Заметки: {entry.get('notes', '')}",
                        "Эмоции: " + ", ".join([e.get("name", "") for e in entry.get("emotions", [])]),
                        "Триггеры: " + ", ".join(entry.get("triggers", [])),
                        "-" * 50
                    ]
                    output.append("\n".join(entry_text))
            
            elif diary_type == DiaryType.THOUGHT:
                # Форматирование для дневника мыслей
                for entry in entries:
                    entry_text = [
                        f"Дата: {entry.get('timestamp', '')}",
                        f"Ситуация: {entry.get('situation', '')}",
                        "Автоматические мысли:",
                    ]
                    
                    for thought in entry.get("automatic_thoughts", []):
                        entry_text.append(f"- {thought.get('content', '')}")
                        entry_text.append(f"  Уровень веры: {thought.get('belief_level', '')}")
                        
                    entry_text.extend([
                        f"Сбалансированная мысль: {entry.get('balanced_thought', '')}",
                        f"Новый уровень веры: {entry.get('new_belief_level', '')}",
                        f"План действий: {entry.get('action_plan', '')}",
                        "-" * 50
                    ])
                    output.append("\n".join(entry_text))
            
            elif diary_type == DiaryType.ACTIVITY:
                # Форматирование для дневника активностей
                for entry in entries:
                    entry_text = [
                        f"Дата: {entry.get('timestamp', '')}",
                        f"Активность ID: {entry.get('activity_id', '')}",
                        f"Статус: {entry.get('status', '')}",
                        f"Оценка: {entry.get('rating', '')}",
                        f"Настроение до: {entry.get('mood_before', '')}",
                        f"Настроение после: {entry.get('mood_after', '')}",
                        f"Энергия до: {entry.get('energy_before', '')}",
                        f"Энергия после: {entry.get('energy_after', '')}",
                        f"Заметки: {entry.get('notes', '')}",
                        "-" * 50
                    ]
                    output.append("\n".join(entry_text))
            
            elif diary_type == DiaryType.INTEGRATIVE:
                # Форматирование для интегративного дневника
                for entry in entries:
                    entry_text = [
                        f"Дата: {entry.get('timestamp', '')}",
                        f"Тип записи: {entry.get('entry_type', '')}",
                        "Диалог:"
                    ]
                    
                    for message in entry.get("conversation", []):
                        entry_text.append(f"- {message.get('role', '')}: {message.get('content', '')}")
                    
                    if "extracted_data" in entry and entry["extracted_data"]:
                        extracted = entry["extracted_data"]
                        entry_text.append(f"Настроение: {extracted.get('mood', '')}")
                        entry_text.append("Эмоции: " + ", ".join(extracted.get("emotions", [])))
                    
                    entry_text.append("-" * 50)
                    output.append("\n".join(entry_text))
            
            return "\n".join(output)
        
        else:
            raise ValueError(f"Неподдерживаемый формат экспорта: {format}")
    
    async def export_all_diaries(
        self,
        user_id: str,
        format: DiaryFormat = DiaryFormat.JSON,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Union[str, bytes]]:
        """
        Экспортирует данные всех дневников пользователя в указанном формате.
        
        Args:
            user_id: ID пользователя
            format: Формат экспорта
            start_date: Начальная дата
            end_date: Конечная дата
            
        Returns:
            Словарь с данными по каждому типу дневника
        """
        results = {}
        
        for diary_type in DiaryType:
            try:
                data = await self.export_diary_data(
                    user_id=user_id,
                    diary_type=diary_type,
                    format=format,
                    start_date=start_date,
                    end_date=end_date
                )
                results[diary_type] = data
            except Exception as e:
                logger.error(f"Error exporting {diary_type} diary: {e}")
                results[diary_type] = f"Error: {str(e)}"
        
        return results