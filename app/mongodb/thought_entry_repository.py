"""
Репозиторий для работы с записями мыслей в MongoDB.
Предоставляет методы для создания, получения и анализа записей мыслей пользователя.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
from bson import ObjectId

from app.mongodb.base_repository import MongoDBBaseRepository

logger = logging.getLogger(__name__)

# Название коллекции для хранения записей мыслей
THOUGHT_ENTRIES_COLLECTION = "thought_entries"


class ThoughtEntryRepository(MongoDBBaseRepository):
    """
    Репозиторий для работы с записями мыслей в MongoDB.
    Наследуется от MongoDBBaseRepository и добавляет специфичные методы
    для работы с записями мыслей и когнитивных искажений.
    """
    
    def __init__(self):
        """
        Инициализирует репозиторий для работы с коллекцией thought_entries.
        """
        super().__init__(THOUGHT_ENTRIES_COLLECTION)
    
    async def init_indexes(self):
        """
        Инициализирует индексы для коллекции thought_entries.
        Вызывается при запуске приложения для обеспечения эффективных запросов.
        """
        db = await self._get_db()
        
        # Основные индексы
        await db[self.collection_name].create_index([("user_id", 1)])
        await db[self.collection_name].create_index([("timestamp", -1)])
        await db[self.collection_name].create_index([("user_id", 1), ("timestamp", -1)])
        
        # Индекс для когнитивных искажений
        await db[self.collection_name].create_index([("automatic_thoughts.cognitive_distortions", 1)])
        
        # Индекс для текстового поиска
        await db[self.collection_name].create_index([
            ("situation", "text"),
            ("automatic_thoughts.content", "text"),
            ("balanced_thought", "text")
        ], name="text_search_index")
        
        # Индекс для отслеживания изменений веры в мысли
        await db[self.collection_name].create_index([
            ("automatic_thoughts.belief_level", 1),
            ("new_belief_level", 1)
        ])
        
        logger.info(f"Created indexes for {self.collection_name}")
    
    async def create_thought_entry(
        self,
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
        
        Args:
            user_id: ID пользователя
            situation: Ситуация, вызвавшая мысли
            automatic_thoughts: Список автоматических мыслей с уровнем веры и когнитивными искажениями
            emotions: Список эмоций с их интенсивностью
            timestamp: Время записи (если не указано, используется текущее время)
            evidence_for: Доказательства, подтверждающие мысль
            evidence_against: Доказательства, опровергающие мысль
            balanced_thought: Сбалансированная мысль
            new_belief_level: Новый уровень веры в мысль после анализа
            action_plan: План действий
            
        Returns:
            str: ID созданной записи
        """
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
        
        # Используем метод create базового репозитория
        return await self.create(thought_entry)
    
    async def get_user_thought_entries(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        skip: int = 0,
        sort_order: int = -1  # -1 для сортировки от новых к старым
    ) -> List[Dict[str, Any]]:
        """
        Получает записи мыслей пользователя с возможностью фильтрации по датам.
        
        Args:
            user_id: ID пользователя
            start_date: Начальная дата для фильтрации
            end_date: Конечная дата для фильтрации
            limit: Максимальное количество записей для возврата
            skip: Количество записей для пропуска (для пагинации)
            sort_order: Порядок сортировки (1 для возрастания, -1 для убывания)
            
        Returns:
            List[Dict[str, Any]]: Список записей мыслей
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
    
    async def search_thought_entries(
        self,
        user_id: str,
        search_text: str,
        limit: int = 100,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Выполняет текстовый поиск по записям мыслей пользователя.
        Использует текстовый индекс MongoDB для эффективного поиска.
        
        Args:
            user_id: ID пользователя
            search_text: Текст для поиска
            limit: Максимальное количество записей для возврата
            skip: Количество записей для пропуска (для пагинации)
            
        Returns:
            List[Dict[str, Any]]: Список записей мыслей, соответствующих поисковому запросу
        """
        db = await self._get_db()
        
        # Формируем запрос с текстовым поиском
        query = {
            "$and": [
                {"user_id": user_id},
                {"$text": {"$search": search_text}}
            ]
        }
        
        # Настраиваем сортировку по релевантности
        sort = [("score", {"$meta": "textScore"})]
        
        # Выполняем запрос с проекцией для получения оценки релевантности
        cursor = db[self.collection_name].find(
            query,
            {"score": {"$meta": "textScore"}}
        ).sort(sort).skip(skip).limit(limit)
        
        results = await cursor.to_list(length=limit)
        
        # Преобразуем ObjectId в строки для JSON-сериализации
        for result in results:
            result["_id"] = str(result["_id"])
        
        return results
    
    async def get_cognitive_distortions_frequency(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Получает частоту когнитивных искажений пользователя.
        
        Args:
            user_id: ID пользователя
            start_date: Начальная дата для фильтрации
            end_date: Конечная дата для фильтрации
            limit: Максимальное количество искажений для возврата
            
        Returns:
            List[Dict[str, Any]]: Список когнитивных искажений с их частотой
        """
        db = await self._get_db()
        
        # Определяем временной диапазон
        match_query = {"user_id": user_id}
        if start_date or end_date:
            date_query = {}
            if start_date:
                date_query["$gte"] = start_date
            if end_date:
                date_query["$lte"] = end_date
            match_query["timestamp"] = date_query
        
        # Формируем агрегационный конвейер
        pipeline = [
            {"$match": match_query},
            {"$unwind": "$automatic_thoughts"},
            {"$unwind": "$automatic_thoughts.cognitive_distortions"},
            {
                "$group": {
                    "_id": "$automatic_thoughts.cognitive_distortions",
                    "count": {"$sum": 1},
                    "entries": {"$addToSet": "$_id"}
                }
            },
            {
                "$project": {
                    "distortion": "$_id",
                    "count": 1,
                    "entry_count": {"$size": "$entries"},
                    "_id": 0
                }
            },
            {"$sort": {"count": -1}},
            {"$limit": limit}
        ]
        
        # Выполняем агрегацию
        return await db[self.collection_name].aggregate(pipeline).to_list(length=limit)
    
    async def get_belief_level_changes(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        interval: str = "month"
    ) -> List[Dict[str, Any]]:
        """
        Получает динамику изменения "веры в мысли" до и после работы с ними.
        
        Args:
            user_id: ID пользователя
            start_date: Начальная дата для фильтрации
            end_date: Конечная дата для фильтрации
            interval: Интервал для агрегации ("day", "week", "month")
            
        Returns:
            List[Dict[str, Any]]: Список с динамикой изменений веры в мысли
        """
        db = await self._get_db()
        
        # Определяем временной диапазон
        if end_date is None:
            end_date = datetime.utcnow()
        
        if start_date is None:
            if interval == "day":
                start_date = end_date - timedelta(days=30)
            elif interval == "week":
                start_date = end_date - timedelta(weeks=12)
            elif interval == "month":
                start_date = end_date - timedelta(days=365)
            else:
                raise ValueError(f"Неподдерживаемый интервал: {interval}")
        
        # Определяем группировку для агрегации
        if interval == "day":
            date_format = "%Y-%m-%d"
        elif interval == "week":
            date_format = "%Y-%U"  # Год-Неделя
        elif interval == "month":
            date_format = "%Y-%m"
        else:
            raise ValueError(f"Неподдерживаемый интервал: {interval}")
        
        # Формируем агрегационный конвейер
        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "timestamp": {"$gte": start_date, "$lte": end_date},
                    "automatic_thoughts": {"$exists": True, "$ne": []},
                    "new_belief_level": {"$exists": True, "$ne": None}
                }
            },
            {
                "$project": {
                    "period": {"$dateToString": {"format": date_format, "date": "$timestamp"}},
                    "initial_belief": {"$arrayElemAt": ["$automatic_thoughts.belief_level", 0]},
                    "new_belief": "$new_belief_level",
                    "belief_change": {
                        "$subtract": [
                            {"$arrayElemAt": ["$automatic_thoughts.belief_level", 0]},
                            "$new_belief_level"
                        ]
                    }
                }
            },
            {
                "$group": {
                    "_id": "$period",
                    "avg_initial_belief": {"$avg": "$initial_belief"},
                    "avg_new_belief": {"$avg": "$new_belief"},
                    "avg_change": {"$avg": "$belief_change"},
                    "entries_count": {"$sum": 1}
                }
            },
            {
                "$sort": {"_id": 1}
            },
            {
                "$project": {
                    "_id": 0,
                    "period": "$_id",
                    "avg_initial_belief": 1,
                    "avg_new_belief": 1,
                    "avg_change": 1,
                    "entries_count": 1
                }
            }
        ]
        
        # Выполняем агрегацию
        return await db[self.collection_name].aggregate(pipeline).to_list(length=100)
    
    async def get_entries_by_distortion(
        self,
        user_id: str,
        distortion: str,
        limit: int = 20,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Получает записи мыслей с конкретным когнитивным искажением.
        
        Args:
            user_id: ID пользователя
            distortion: Название когнитивного искажения
            limit: Максимальное количество записей для возврата
            skip: Количество записей для пропуска (для пагинации)
            
        Returns:
            List[Dict[str, Any]]: Список записей мыслей с указанным искажением
        """
        db = await self._get_db()
        
        # Формируем запрос для поиска записей с указанным искажением
        query = {
            "user_id": user_id,
            "automatic_thoughts.cognitive_distortions": distortion
        }
        
        # Выполняем запрос
        cursor = db[self.collection_name].find(query).sort("timestamp", -1).skip(skip).limit(limit)
        results = await cursor.to_list(length=limit)
        
        # Преобразуем ObjectId в строки для JSON-сериализации
        for result in results:
            result["_id"] = str(result["_id"])
        
        return results
    
    async def get_thought_statistics(
        self,
        user_id: str,
        period: str = "week",  # "day", "week", "month", "year", "all"
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Получает статистику мыслей пользователя за указанный период.
        
        Args:
            user_id: ID пользователя
            period: Период для расчета статистики ("day", "week", "month", "year", "all")
            end_date: Конечная дата периода (если не указана, используется текущая дата)
            
        Returns:
            Dict[str, Any]: Статистика мыслей
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
        entries = await self.get_user_thought_entries(
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
                "top_distortions": [],
                "belief_change_avg": None,
                "emotions_frequency": [],
                "completed_percentage": 0
            }
        
        # Анализируем когнитивные искажения
        distortion_counter = {}
        belief_changes = []
        emotion_counter = {}
        completed_entries = 0
        
        for entry in entries:
            # Проверяем, завершена ли запись
            if "balanced_thought" in entry and entry["balanced_thought"] and "new_belief_level" in entry and entry["new_belief_level"] is not None:
                completed_entries += 1
            
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
        
        # Процент завершенных записей
        completed_percentage = (completed_entries / len(entries) * 100) if entries else 0
        
        return {
            "period": period,
            "start_date": start_date,
            "end_date": end_date,
            "count": len(entries),
            "top_distortions": [{"name": name, "count": count} for name, count in top_distortions],
            "belief_change_avg": belief_change_avg,
            "emotions_frequency": [{"name": name, "count": count} for name, count in emotions_frequency],
            "completed_percentage": completed_percentage
        }