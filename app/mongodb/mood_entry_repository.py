"""
Репозиторий для работы с записями настроения в MongoDB.
Предоставляет методы для создания, получения и анализа записей настроения пользователя.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
from bson import ObjectId

from app.mongodb.base_repository import MongoDBBaseRepository
from app.mongodb.mood_thought_schemas import create_timestamped_document

logger = logging.getLogger(__name__)

# Название коллекции для хранения записей настроения
MOOD_ENTRIES_COLLECTION = "mood_entries"


class MoodEntryRepository(MongoDBBaseRepository):
    """
    Репозиторий для работы с записями настроения в MongoDB.
    Наследуется от MongoDBBaseRepository и добавляет специфичные методы
    для работы с записями настроения.
    """
    
    def __init__(self):
        """
        Инициализирует репозиторий для работы с коллекцией mood_entries.
        """
        super().__init__(MOOD_ENTRIES_COLLECTION)
    
    async def create_mood_entry(
        self,
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
        
        Args:
            user_id: ID пользователя
            mood_score: Оценка настроения по шкале от -10 до 10
            emotions: Список эмоций с их интенсивностью
            timestamp: Время записи (если не указано, используется текущее время)
            triggers: Факторы, вызвавшие эмоции
            physical_sensations: Физические ощущения
            body_areas: Зоны тела с ощущениями
            context: Контекст записи
            notes: Заметки пользователя
            
        Returns:
            str: ID созданной записи
        """
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
        
        # Используем метод create базового репозитория
        return await self.create(mood_entry)
    
    async def get_user_mood_entries(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        skip: int = 0,
        sort_order: int = -1  # -1 для сортировки от новых к старым
    ) -> List[Dict[str, Any]]:
        """
        Получает записи настроения пользователя с возможностью фильтрации по датам.
        
        Args:
            user_id: ID пользователя
            start_date: Начальная дата для фильтрации
            end_date: Конечная дата для фильтрации
            limit: Максимальное количество записей для возврата
            skip: Количество записей для пропуска (для пагинации)
            sort_order: Порядок сортировки (1 для возрастания, -1 для убывания)
            
        Returns:
            List[Dict[str, Any]]: Список записей настроения
        """
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
        
        # Используем метод get_many базового репозитория
        return await self.get_many(
            query=query,
            skip=skip,
            limit=limit,
            sort_by="timestamp",
            sort_order=sort_order
        )
    
    async def get_last_mood_entry(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает последнюю запись настроения пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Optional[Dict[str, Any]]: Последняя запись настроения или None, если записей нет
        """
        entries = await self.get_user_mood_entries(user_id, limit=1)
        return entries[0] if entries else None
    
    async def get_user_mood_trends(
        self,
        user_id: str,
        interval: str = "day",  # "day", "week", "month"
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 30  # Ограничение на количество точек данных
    ) -> List[Dict[str, Any]]:
        """
        Получает тренды настроения пользователя с агрегацией по интервалам.
        
        Args:
            user_id: ID пользователя
            interval: Интервал для агрегации ("day", "week", "month")
            start_date: Начальная дата для фильтрации
            end_date: Конечная дата для фильтрации
            limit: Максимальное количество точек данных
            
        Returns:
            List[Dict[str, Any]]: Список трендов настроения
        """
        db = await self._get_db()
        
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
        
        return await db[self.collection_name].aggregate(pipeline).to_list(length=limit)
    
    async def get_mood_statistics(
        self,
        user_id: str,
        period: str = "week",  # "day", "week", "month", "year", "all"
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Получает статистику настроения пользователя за указанный период.
        
        Args:
            user_id: ID пользователя
            period: Период для расчета статистики ("day", "week", "month", "year", "all")
            end_date: Конечная дата периода (если не указана, используется текущая дата)
            
        Returns:
            Dict[str, Any]: Статистика настроения
        """
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
        
        # Получаем записи за период
        entries = await self.get_user_mood_entries(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=1000  # Ограничение на количество записей
        )
        
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