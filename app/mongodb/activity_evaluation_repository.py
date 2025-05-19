"""
Репозиторий для работы с оценками активностей в MongoDB.
Предоставляет методы для создания, получения и анализа оценок активностей.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
from bson import ObjectId

from app.mongodb.base_repository import MongoDBBaseRepository

logger = logging.getLogger(__name__)

# Название коллекции для хранения оценок активностей
ACTIVITY_EVALUATIONS_COLLECTION = "activity_evaluations"


class ActivityEvaluationRepository(MongoDBBaseRepository):
    """
    Репозиторий для работы с оценками активностей в MongoDB.
    Наследуется от MongoDBBaseRepository и добавляет специфичные методы
    для работы с оценками и анализа эффективности активностей.
    """
    
    def __init__(self):
        """
        Инициализирует репозиторий для работы с коллекцией activity_evaluations.
        """
        super().__init__(ACTIVITY_EVALUATIONS_COLLECTION)
    
    async def init_indexes(self):
        """
        Инициализирует индексы для коллекции activity_evaluations.
        Вызывается при запуске приложения для обеспечения эффективных запросов.
        """
        db = await self._get_db()
        
        # Основные индексы
        await db[self.collection_name].create_index([("user_id", 1)])
        await db[self.collection_name].create_index([("activity_id", 1)])
        await db[self.collection_name].create_index([("timestamp", -1)])
        await db[self.collection_name].create_index([("user_id", 1), ("activity_id", 1)])
        await db[self.collection_name].create_index([("user_id", 1), ("timestamp", -1)])
        await db[self.collection_name].create_index([("activity_id", 1), ("timestamp", -1)])
        
        # Индекс для агрегаций по оценкам
        await db[self.collection_name].create_index([("satisfaction_score", 1)])
        await db[self.collection_name].create_index([("difficulty_score", 1)])
        
        # Составной индекс для часто используемых запросов
        await db[self.collection_name].create_index([
            ("user_id", 1),
            ("activity_id", 1),
            ("timestamp", -1)
        ])
        
        # Индекс для эмоционального состояния до и после активности
        await db[self.collection_name].create_index([("mood_before", 1)])
        await db[self.collection_name].create_index([("mood_after", 1)])
        
        logger.info(f"Created indexes for {self.collection_name}")
    
    async def create_activity_evaluation(
        self,
        user_id: str,
        activity_id: str,
        satisfaction_score: float,  # 1-10
        difficulty_score: Optional[float] = None,  # 1-10
        mood_before: Optional[float] = None,  # -10 до +10
        mood_after: Optional[float] = None,  # -10 до +10
        energy_before: Optional[float] = None,  # -10 до +10
        energy_after: Optional[float] = None,  # -10 до +10
        notes: Optional[str] = None,
        emotion_changes: Optional[List[Dict[str, Any]]] = None,
        need_satisfaction: Optional[Dict[str, float]] = None,
        duration_minutes: Optional[int] = None,
        completion_percentage: Optional[float] = None,
        timestamp: Optional[datetime] = None
    ) -> str:
        """
        Создает новую оценку активности.
        
        Args:
            user_id: ID пользователя
            activity_id: ID активности
            satisfaction_score: Оценка удовлетворенности от 1 до 10
            difficulty_score: Оценка сложности от 1 до 10
            mood_before: Настроение до активности от -10 до +10
            mood_after: Настроение после активности от -10 до +10
            energy_before: Энергия до активности от -10 до +10
            energy_after: Энергия после активности от -10 до +10
            notes: Заметки пользователя
            emotion_changes: Изменения в эмоциональном состоянии
            need_satisfaction: Удовлетворение различных потребностей
            duration_minutes: Длительность активности в минутах
            completion_percentage: Процент завершения активности
            timestamp: Время оценки (если не указано, используется текущее время)
            
        Returns:
            str: ID созданной оценки
        """
        evaluation = {
            "user_id": user_id,
            "activity_id": activity_id,
            "satisfaction_score": satisfaction_score,
            "timestamp": timestamp or datetime.utcnow()
        }
        
        # Добавляем опциональные поля, если они предоставлены
        if difficulty_score is not None:
            evaluation["difficulty_score"] = difficulty_score
        if mood_before is not None:
            evaluation["mood_before"] = mood_before
        if mood_after is not None:
            evaluation["mood_after"] = mood_after
        if energy_before is not None:
            evaluation["energy_before"] = energy_before
        if energy_after is not None:
            evaluation["energy_after"] = energy_after
        if notes:
            evaluation["notes"] = notes
        if emotion_changes:
            evaluation["emotion_changes"] = emotion_changes
        if need_satisfaction:
            evaluation["need_satisfaction"] = need_satisfaction
        if duration_minutes is not None:
            evaluation["duration_minutes"] = duration_minutes
        if completion_percentage is not None:
            evaluation["completion_percentage"] = completion_percentage
        
        # Предварительный расчет изменений
        if mood_before is not None and mood_after is not None:
            evaluation["mood_change"] = mood_after - mood_before
        if energy_before is not None and energy_after is not None:
            evaluation["energy_change"] = energy_after - energy_before
        
        # Используем метод create базового репозитория
        return await self.create(evaluation)
    
    async def get_activity_evaluations(
        self,
        activity_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        skip: int = 0,
        sort_order: int = -1  # -1 для сортировки от новых к старым
    ) -> List[Dict[str, Any]]:
        """
        Получает оценки для конкретной активности с возможностью фильтрации по датам.
        
        Args:
            activity_id: ID активности
            start_date: Начальная дата для фильтрации
            end_date: Конечная дата для фильтрации
            limit: Максимальное количество оценок для возврата
            skip: Количество оценок для пропуска (для пагинации)
            sort_order: Порядок сортировки (1 для возрастания, -1 для убывания)
            
        Returns:
            List[Dict[str, Any]]: Список оценок активности
        """
        # Создаем базовый запрос
        query = {"activity_id": activity_id}
        
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
    
    async def get_user_activity_evaluations(
        self,
        user_id: str,
        activity_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        skip: int = 0,
        sort_order: int = -1  # -1 для сортировки от новых к старым
    ) -> List[Dict[str, Any]]:
        """
        Получает оценки активностей конкретного пользователя с возможностью фильтрации.
        
        Args:
            user_id: ID пользователя
            activity_id: ID активности (опционально)
            start_date: Начальная дата для фильтрации
            end_date: Конечная дата для фильтрации
            limit: Максимальное количество оценок для возврата
            skip: Количество оценок для пропуска (для пагинации)
            sort_order: Порядок сортировки (1 для возрастания, -1 для убывания)
            
        Returns:
            List[Dict[str, Any]]: Список оценок активностей пользователя
        """
        # Создаем базовый запрос
        query = {"user_id": user_id}
        
        # Добавляем фильтр по активности, если указан
        if activity_id:
            query["activity_id"] = activity_id
        
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
    
    async def get_activity_average_satisfaction(
        self,
        activity_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Рассчитывает среднюю оценку удовлетворенности и сложности для активности.
        
        Args:
            activity_id: ID активности
            start_date: Начальная дата для фильтрации
            end_date: Конечная дата для фильтрации
            
        Returns:
            Dict[str, Any]: Средние оценки и статистика
        """
        db = await self._get_db()
        
        # Создаем запрос
        match_query = {"activity_id": activity_id}
        if start_date or end_date:
            date_query = {}
            if start_date:
                date_query["$gte"] = start_date
            if end_date:
                date_query["$lte"] = end_date
            match_query["timestamp"] = date_query
        
        # Агрегационный конвейер
        pipeline = [
            {"$match": match_query},
            {
                "$group": {
                    "_id": "$activity_id",
                    "avg_satisfaction": {"$avg": "$satisfaction_score"},
                    "avg_difficulty": {"$avg": "$difficulty_score"},
                    "avg_mood_change": {"$avg": "$mood_change"},
                    "avg_energy_change": {"$avg": "$energy_change"},
                    "avg_completion": {"$avg": "$completion_percentage"},
                    "count": {"$sum": 1},
                    "users_count": {"$addToSet": "$user_id"}
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "activity_id": "$_id",
                    "avg_satisfaction": 1,
                    "avg_difficulty": 1,
                    "avg_mood_change": 1,
                    "avg_energy_change": 1,
                    "avg_completion": 1,
                    "evaluations_count": "$count",
                    "users_count": {"$size": "$users_count"}
                }
            }
        ]
        
        # Выполняем агрегацию
        results = await db[self.collection_name].aggregate(pipeline).to_list(length=1)
        
        if not results:
            return {
                "activity_id": activity_id,
                "avg_satisfaction": None,
                "avg_difficulty": None,
                "avg_mood_change": None,
                "avg_energy_change": None,
                "avg_completion": None,
                "evaluations_count": 0,
                "users_count": 0
            }
        
        return results[0]
    
    async def get_activity_state_impact(
        self,
        activity_id: str,
        period: str = "all",
        interval: Optional[str] = None
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Получает статистику влияния активности на состояние пользователя.
        
        Args:
            activity_id: ID активности
            period: Период для анализа ("week", "month", "year", "all")
            interval: Интервал для группировки результатов (None, "day", "week", "month")
            
        Returns:
            Union[Dict[str, Any], List[Dict[str, Any]]]: Статистика влияния на состояние
        """
        db = await self._get_db()
        
        # Определяем временной диапазон
        end_date = datetime.utcnow()
        if period == "week":
            start_date = end_date - timedelta(days=7)
        elif period == "month":
            start_date = end_date - timedelta(days=30)
        elif period == "year":
            start_date = end_date - timedelta(days=365)
        else:  # "all"
            start_date = datetime.min
        
        # Базовый запрос
        match_query = {
            "activity_id": activity_id,
            "timestamp": {"$gte": start_date, "$lte": end_date},
            # Требуем наличие данных об изменении состояния
            "$or": [
                {"mood_before": {"$exists": True}, "mood_after": {"$exists": True}},
                {"energy_before": {"$exists": True}, "energy_after": {"$exists": True}}
            ]
        }
        
        # Если интервал не указан, просто возвращаем общую статистику
        if not interval:
            pipeline = [
                {"$match": match_query},
                {
                    "$group": {
                        "_id": "$activity_id",
                        "evaluations_count": {"$sum": 1},
                        "avg_mood_before": {"$avg": "$mood_before"},
                        "avg_mood_after": {"$avg": "$mood_after"},
                        "avg_mood_change": {"$avg": {"$subtract": ["$mood_after", "$mood_before"]}},
                        "avg_energy_before": {"$avg": "$energy_before"},
                        "avg_energy_after": {"$avg": "$energy_after"},
                        "avg_energy_change": {"$avg": {"$subtract": ["$energy_after", "$energy_before"]}},
                        "positive_mood_impact_count": {
                            "$sum": {
                                "$cond": [
                                    {"$gt": [{"$subtract": ["$mood_after", "$mood_before"]}, 0]},
                                    1,
                                    0
                                ]
                            }
                        },
                        "negative_mood_impact_count": {
                            "$sum": {
                                "$cond": [
                                    {"$lt": [{"$subtract": ["$mood_after", "$mood_before"]}, 0]},
                                    1,
                                    0
                                ]
                            }
                        },
                        "positive_energy_impact_count": {
                            "$sum": {
                                "$cond": [
                                    {"$gt": [{"$subtract": ["$energy_after", "$energy_before"]}, 0]},
                                    1,
                                    0
                                ]
                            }
                        },
                        "negative_energy_impact_count": {
                            "$sum": {
                                "$cond": [
                                    {"$lt": [{"$subtract": ["$energy_after", "$energy_before"]}, 0]},
                                    1,
                                    0
                                ]
                            }
                        },
                        "satisfaction_scores": {"$push": "$satisfaction_score"},
                        "need_satisfaction": {"$push": "$need_satisfaction"}
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "activity_id": "$_id",
                        "evaluations_count": 1,
                        "avg_mood_before": 1,
                        "avg_mood_after": 1,
                        "avg_mood_change": 1,
                        "avg_energy_before": 1,
                        "avg_energy_after": 1,
                        "avg_energy_change": 1,
                        "positive_mood_impact_percentage": {
                            "$multiply": [
                                {"$divide": ["$positive_mood_impact_count", "$evaluations_count"]},
                                100
                            ]
                        },
                        "negative_mood_impact_percentage": {
                            "$multiply": [
                                {"$divide": ["$negative_mood_impact_count", "$evaluations_count"]},
                                100
                            ]
                        },
                        "positive_energy_impact_percentage": {
                            "$multiply": [
                                {"$divide": ["$positive_energy_impact_count", "$evaluations_count"]},
                                100
                            ]
                        },
                        "negative_energy_impact_percentage": {
                            "$multiply": [
                                {"$divide": ["$negative_energy_impact_count", "$evaluations_count"]},
                                100
                            ]
                        }
                    }
                }
            ]
            
            results = await db[self.collection_name].aggregate(pipeline).to_list(length=1)
            
            if not results:
                return {
                    "activity_id": activity_id,
                    "evaluations_count": 0,
                    "avg_mood_before": None,
                    "avg_mood_after": None,
                    "avg_mood_change": None,
                    "avg_energy_before": None,
                    "avg_energy_after": None,
                    "avg_energy_change": None,
                    "positive_mood_impact_percentage": None,
                    "negative_mood_impact_percentage": None,
                    "positive_energy_impact_percentage": None,
                    "negative_energy_impact_percentage": None
                }
            
            return results[0]
        
        # Если указан интервал, группируем по временным периодам
        date_group_format = None
        if interval == "day":
            date_group_format = "%Y-%m-%d"
        elif interval == "week":
            date_group_format = "%Y-%U"
        elif interval == "month":
            date_group_format = "%Y-%m"
        else:
            raise ValueError(f"Неподдерживаемый интервал: {interval}")
        
        pipeline = [
            {"$match": match_query},
            {
                "$group": {
                    "_id": {
                        "activity_id": "$activity_id",
                        "period": {"$dateToString": {"format": date_group_format, "date": "$timestamp"}}
                    },
                    "evaluations_count": {"$sum": 1},
                    "avg_mood_before": {"$avg": "$mood_before"},
                    "avg_mood_after": {"$avg": "$mood_after"},
                    "avg_mood_change": {"$avg": {"$subtract": ["$mood_after", "$mood_before"]}},
                    "avg_energy_before": {"$avg": "$energy_before"},
                    "avg_energy_after": {"$avg": "$energy_after"},
                    "avg_energy_change": {"$avg": {"$subtract": ["$energy_after", "$energy_before"]}},
                    "first_date": {"$min": "$timestamp"},
                    "last_date": {"$max": "$timestamp"}
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "activity_id": "$_id.activity_id",
                    "period": "$_id.period",
                    "evaluations_count": 1,
                    "avg_mood_before": 1,
                    "avg_mood_after": 1,
                    "avg_mood_change": 1,
                    "avg_energy_before": 1,
                    "avg_energy_after": 1,
                    "avg_energy_change": 1,
                    "first_date": 1,
                    "last_date": 1
                }
            },
            {"$sort": {"period": 1}}
        ]
        
        return await db[self.collection_name].aggregate(pipeline).to_list(length=100)
    
    async def get_user_activity_statistics(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Получает статистику по активностям пользователя: наиболее эффективные, 
        часто используемые и т.д.
        
        Args:
            user_id: ID пользователя
            start_date: Начальная дата для фильтрации
            end_date: Конечная дата для фильтрации
            limit: Максимальное количество активностей для возврата
            
        Returns:
            List[Dict[str, Any]]: Статистика по активностям пользователя
        """
        db = await self._get_db()
        
        # Определяем временной диапазон
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=90)  # За последние 3 месяца
        
        # Формируем базовый запрос
        match_query = {
            "user_id": user_id,
            "timestamp": {"$gte": start_date, "$lte": end_date}
        }
        
        # Агрегационный конвейер для получения статистики по активностям
        pipeline = [
            {"$match": match_query},
            {
                "$group": {
                    "_id": "$activity_id",
                    "count": {"$sum": 1},
                    "avg_satisfaction": {"$avg": "$satisfaction_score"},
                    "avg_mood_change": {
                        "$avg": {
                            "$cond": [
                                {"$and": [
                                    {"$ifNull": ["$mood_before", False]},
                                    {"$ifNull": ["$mood_after", False]}
                                ]},
                                {"$subtract": ["$mood_after", "$mood_before"]},
                                None
                            ]
                        }
                    },
                    "avg_energy_change": {
                        "$avg": {
                            "$cond": [
                                {"$and": [
                                    {"$ifNull": ["$energy_before", False]},
                                    {"$ifNull": ["$energy_after", False]}
                                ]},
                                {"$subtract": ["$energy_after", "$energy_before"]},
                                None
                            ]
                        }
                    },
                    "last_used": {"$max": "$timestamp"}
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "activity_id": "$_id",
                    "count": 1,
                    "avg_satisfaction": 1,
                    "avg_mood_change": 1,
                    "avg_energy_change": 1,
                    "last_used": 1,
                    # Рассчитываем сводный показатель эффективности
                    "effectiveness_score": {
                        "$add": [
                            {"$multiply": [{"$ifNull": ["$avg_satisfaction", 0]}, 0.5]},
                            {"$multiply": [{"$ifNull": ["$avg_mood_change", 0]}, 2]},
                            {"$multiply": [{"$ifNull": ["$avg_energy_change", 0]}, 2]}
                        ]
                    }
                }
            },
            {"$sort": {"effectiveness_score": -1}},
            {"$limit": limit}
        ]
        
        return await db[self.collection_name].aggregate(pipeline).to_list(length=limit)
    
    async def get_need_satisfaction_by_activity(
        self,
        activity_id: Optional[str] = None,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Анализирует, какие потребности удовлетворяются через указанную активность.
        
        Args:
            activity_id: ID активности (опционально)
            user_id: ID пользователя (опционально)
            start_date: Начальная дата для фильтрации
            end_date: Конечная дата для фильтрации
            
        Returns:
            List[Dict[str, Any]]: Статистика по удовлетворению потребностей
        """
        db = await self._get_db()
        
        # Формируем базовый запрос
        match_query = {"need_satisfaction": {"$exists": True, "$ne": {}}}
        
        if activity_id:
            match_query["activity_id"] = activity_id
        if user_id:
            match_query["user_id"] = user_id
        
        # Добавляем фильтры по датам, если они указаны
        if start_date or end_date:
            date_query = {}
            if start_date:
                date_query["$gte"] = start_date
            if end_date:
                date_query["$lte"] = end_date
            match_query["timestamp"] = date_query
        
        # Этап 1: "Разворачиваем" объект need_satisfaction в пары ключ-значение
        pipeline_stage1 = [
            {"$match": match_query},
            {"$project": {
                "activity_id": 1,
                "need_satisfaction": {"$objectToArray": "$need_satisfaction"}
            }},
            {"$unwind": "$need_satisfaction"},
            {"$project": {
                "activity_id": 1,
                "need_name": "$need_satisfaction.k",
                "satisfaction_value": "$need_satisfaction.v"
            }}
        ]
        
        # Этап 2: Группируем по активности и потребности
        group_id = {}
        if activity_id:
            group_id["need_name"] = "$need_name"
        else:
            group_id["activity_id"] = "$activity_id"
            group_id["need_name"] = "$need_name"
        
        pipeline_stage2 = [
            {"$group": {
                "_id": group_id,
                "avg_satisfaction": {"$avg": "$satisfaction_value"},
                "count": {"$sum": 1}
            }},
            {"$sort": {"avg_satisfaction": -1}}
        ]
        
        # Этап 3: Форматируем результат
        pipeline_stage3 = []
        if activity_id:
            pipeline_stage3 = [
                {"$project": {
                    "_id": 0,
                    "activity_id": activity_id,
                    "need_name": "$_id.need_name",
                    "avg_satisfaction": 1,
                    "count": 1
                }}
            ]
        else:
            pipeline_stage3 = [
                {"$project": {
                    "_id": 0,
                    "activity_id": "$_id.activity_id",
                    "need_name": "$_id.need_name",
                    "avg_satisfaction": 1,
                    "count": 1
                }}
            ]
        
        # Объединяем этапы
        pipeline = pipeline_stage1 + pipeline_stage2 + pipeline_stage3
        
        return await db[self.collection_name].aggregate(pipeline).to_list(length=100)
    
    async def get_activities_by_effectiveness(
        self,
        criteria: str = "mood",  # "mood", "energy", "satisfaction", "overall"
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        min_evaluations: int = 3,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Получает наиболее эффективные активности по указанному критерию.
        
        Args:
            criteria: Критерий эффективности ("mood", "energy", "satisfaction", "overall")
            user_id: ID пользователя (опционально)
            start_date: Начальная дата для фильтрации
            end_date: Конечная дата для фильтрации
            min_evaluations: Минимальное количество оценок для анализа
            limit: Максимальное количество активностей для возврата
            
        Returns:
            List[Dict[str, Any]]: Список наиболее эффективных активностей
        """
        db = await self._get_db()
        
        # Формируем базовый запрос
        match_query = {}
        if user_id:
            match_query["user_id"] = user_id
        
        # Добавляем фильтры по датам, если они указаны
        if start_date or end_date:
            date_query = {}
            if start_date:
                date_query["$gte"] = start_date
            if end_date:
                date_query["$lte"] = end_date
            match_query["timestamp"] = date_query
        
        # Дополнительные условия в зависимости от критерия
        if criteria == "mood":
            match_query["mood_before"] = {"$exists": True}
            match_query["mood_after"] = {"$exists": True}
        elif criteria == "energy":
            match_query["energy_before"] = {"$exists": True}
            match_query["energy_after"] = {"$exists": True}
        elif criteria == "satisfaction":
            match_query["satisfaction_score"] = {"$exists": True}
        
        # Агрегационный конвейер
        pipeline = [
            {"$match": match_query},
            {
                "$group": {
                    "_id": "$activity_id",
                    "count": {"$sum": 1},
                    "avg_satisfaction": {"$avg": "$satisfaction_score"},
                    "avg_mood_change": {
                        "$avg": {
                            "$cond": [
                                {"$and": [
                                    {"$ifNull": ["$mood_before", False]},
                                    {"$ifNull": ["$mood_after", False]}
                                ]},
                                {"$subtract": ["$mood_after", "$mood_before"]},
                                0
                            ]
                        }
                    },
                    "avg_energy_change": {
                        "$avg": {
                            "$cond": [
                                {"$and": [
                                    {"$ifNull": ["$energy_before", False]},
                                    {"$ifNull": ["$energy_after", False]}
                                ]},
                                {"$subtract": ["$energy_after", "$energy_before"]},
                                0
                            ]
                        }
                    }
                }
            },
            {
                "$match": {
                    "count": {"$gte": min_evaluations}
                }
            }
        ]
        
        # Добавляем сортировку в зависимости от критерия
        sort_field = ""
        if criteria == "mood":
            sort_field = "avg_mood_change"
        elif criteria == "energy":
            sort_field = "avg_energy_change"
        elif criteria == "satisfaction":
            sort_field = "avg_satisfaction"
        elif criteria == "overall":
            # Проекция для расчета общей эффективности
            pipeline.append({
                "$project": {
                    "_id": 0,
                    "activity_id": "$_id",
                    "count": 1,
                    "avg_satisfaction": 1,
                    "avg_mood_change": 1,
                    "avg_energy_change": 1,
                    "overall_effectiveness": {
                        "$add": [
                            {"$multiply": [{"$ifNull": ["$avg_satisfaction", 0]}, 0.5]},
                            {"$multiply": [{"$ifNull": ["$avg_mood_change", 0]}, 2]},
                            {"$multiply": [{"$ifNull": ["$avg_energy_change", 0]}, 2]}
                        ]
                    }
                }
            })
            sort_field = "overall_effectiveness"
        else:
            raise ValueError(f"Неподдерживаемый критерий: {criteria}")
        
        if criteria != "overall":
            pipeline.append({
                "$project": {
                    "_id": 0,
                    "activity_id": "$_id",
                    "count": 1,
                    "avg_satisfaction": 1,
                    "avg_mood_change": 1,
                    "avg_energy_change": 1
                }
            })
        
        pipeline.append({"$sort": {sort_field: -1}})
        pipeline.append({"$limit": limit})
        
        return await db[self.collection_name].aggregate(pipeline).to_list(length=limit)