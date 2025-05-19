"""
Репозиторий для работы с активностями пользователей.
"""
from typing import List, Optional, Dict, Any, Union, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, func, and_, or_, or_
from sqlalchemy.sql import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.repositories.base_repository import BaseRepository
from app.models.activity import Activity
from app.models.activity_types import ActivityType, ActivitySubtype


class ActivityRepository(BaseRepository):
    """
    Репозиторий для работы с активностями пользователей.
    Наследуется от BaseRepository и добавляет специфические методы для модели Activity.
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Инициализация репозитория.
        
        Args:
            db_session: Асинхронная сессия базы данных
        """
        super().__init__(db_session, Activity)
    
    async def get_activity_by_id(self, activity_id: UUID) -> Optional[Activity]:
        """
        Получение активности по ID.
        
        Args:
            activity_id: UUID активности
            
        Returns:
            Объект активности или None, если активность не найдена
        """
        try:
            return await self.get_by_id(activity_id)
        except Exception as e:
            # Обработка ошибок (логирование, специфичная обработка и т.д.)
            # Возможно здесь стоит добавить логирование
            raise e
    
    async def get_activity_by_id_with_relations(self, activity_id: UUID) -> Optional[Activity]:
        """
        Получение активности по ID со всеми связанными данными.
        
        Args:
            activity_id: UUID активности
            
        Returns:
            Объект активности со связанными данными или None, если активность не найдена
        """
        try:
            query = (
                select(Activity)
                .options(
                    joinedload(Activity.activity_type),
                    joinedload(Activity.activity_subtype),
                    joinedload(Activity.activity_needs).joinedload(Activity.activity_needs.need)
                )
                .where(Activity.id == activity_id)
            )
            result = await self.db.execute(query)
            return result.scalars().first()
        except Exception as e:
            # Обработка ошибок
            raise e
    
    async def create_activity(self, activity_data: Dict[str, Any]) -> Activity:
        """
        Создание новой активности.
        
        Args:
            activity_data: Словарь с данными активности
            
        Returns:
            Созданный объект активности
        
        Raises:
            Exception: При ошибке создания активности
        """
        try:
            # Если продолжительность не передана, рассчитываем её на основе времени начала и окончания
            if "start_time" in activity_data and "end_time" in activity_data and "duration_minutes" not in activity_data:
                start_time = activity_data["start_time"]
                end_time = activity_data["end_time"]
                if isinstance(start_time, str):
                    start_time = datetime.fromisoformat(start_time)
                if isinstance(end_time, str):
                    end_time = datetime.fromisoformat(end_time)
                
                duration_minutes = int((end_time - start_time).total_seconds() / 60)
                activity_data["duration_minutes"] = duration_minutes
            
            # Создаем активность через базовый метод
            return await self.create(activity_data)
        except Exception as e:
            # Обработка ошибок создания активности
            raise e
    
    async def update_activity(self, activity_id: UUID, activity_data: Dict[str, Any]) -> Optional[Activity]:
        """
        Обновление активности.
        
        Args:
            activity_id: UUID активности
            activity_data: Словарь с обновленными данными активности
            
        Returns:
            Обновленный объект активности или None, если активность не найдена
            
        Raises:
            Exception: При ошибке обновления активности
        """
        try:
            # Если меняются start_time или end_time, обновляем duration_minutes
            if ("start_time" in activity_data or "end_time" in activity_data):
                # Получаем текущую активность
                activity = await self.get_by_id(activity_id)
                if not activity:
                    return None
                
                # Определяем времена начала и окончания
                start_time = activity_data.get("start_time", activity.start_time)
                end_time = activity_data.get("end_time", activity.end_time)
                
                # Преобразуем строковые значения в datetime
                if isinstance(start_time, str):
                    start_time = datetime.fromisoformat(start_time)
                if isinstance(end_time, str):
                    end_time = datetime.fromisoformat(end_time)
                
                # Рассчитываем продолжительность
                duration_minutes = int((end_time - start_time).total_seconds() / 60)
                activity_data["duration_minutes"] = duration_minutes
            
            # Обновляем активность через базовый метод
            return await self.update(activity_id, activity_data)
        except Exception as e:
            # Обработка ошибок обновления активности
            raise e
    
    async def delete_activity(self, activity_id: UUID) -> bool:
        """
        Мягкое удаление активности (установка is_active=False).
        
        Args:
            activity_id: UUID активности
            
        Returns:
            True, если активность успешно удалена, иначе False
            
        Raises:
            Exception: При ошибке удаления активности
        """
        try:
            # Используем метод soft_delete из базового репозитория
            return await self.delete(activity_id, soft_delete=True)
        except Exception as e:
            # Обработка ошибок удаления активности
            raise e
    
    async def get_activities_by_type(
        self, 
        type_id: UUID, 
        pagination: Optional[Dict[str, int]] = None,
        user_id: Optional[UUID] = None,
        include_inactive: bool = False
    ) -> Tuple[List[Activity], int]:
        """
        Получение активностей по типу с поддержкой пагинации.
        
        Args:
            type_id: UUID типа активности
            pagination: Словарь с параметрами пагинации {'skip': int, 'limit': int}
            user_id: Опциональный UUID пользователя для фильтрации
            include_inactive: Если True, включать неактивные активности
            
        Returns:
            Кортеж (список активностей, общее количество)
        """
        try:
            # Строим базовый запрос
            filters = {"activity_type_id": type_id}
            
            # Добавляем фильтр по пользователю, если указан
            if user_id:
                filters["user_id"] = user_id
                
            # Добавляем фильтр по активности элементов
            if not include_inactive:
                filters["is_active"] = True
            
            # Получаем общее количество
            total_count = await self.count(filters)
            
            # Получаем список с учетом пагинации
            order_by = ["-start_time"]  # Сортировка по дате начала (от новых к старым)
            activities = await self.list(filters, pagination, order_by)
            
            return activities, total_count
        except Exception as e:
            # Обработка ошибок
            raise e
    
    async def get_activities_by_subtype(
        self, 
        subtype_id: UUID, 
        pagination: Optional[Dict[str, int]] = None,
        user_id: Optional[UUID] = None,
        include_inactive: bool = False
    ) -> Tuple[List[Activity], int]:
        """
        Получение активностей по подтипу с поддержкой пагинации.
        
        Args:
            subtype_id: UUID подтипа активности
            pagination: Словарь с параметрами пагинации {'skip': int, 'limit': int}
            user_id: Опциональный UUID пользователя для фильтрации
            include_inactive: Если True, включать неактивные активности
            
        Returns:
            Кортеж (список активностей, общее количество)
        """
        try:
            # Строим базовый запрос
            filters = {"activity_subtype_id": subtype_id}
            
            # Добавляем фильтр по пользователю, если указан
            if user_id:
                filters["user_id"] = user_id
                
            # Добавляем фильтр по активности элементов
            if not include_inactive:
                filters["is_active"] = True
            
            # Получаем общее количество
            total_count = await self.count(filters)
            
            # Получаем список с учетом пагинации
            order_by = ["-start_time"]  # Сортировка по дате начала (от новых к старым)
            activities = await self.list(filters, pagination, order_by)
            
            return activities, total_count
        except Exception as e:
            # Обработка ошибок
            raise e
    
    async def search_activities(
        self, 
        search_term: str, 
        pagination: Optional[Dict[str, int]] = None,
        user_id: Optional[UUID] = None,
        include_inactive: bool = False
    ) -> Tuple[List[Activity], int]:
        """
        Поиск активностей по названию или описанию с поддержкой пагинации.
        
        Args:
            search_term: Строка для поиска
            pagination: Словарь с параметрами пагинации {'skip': int, 'limit': int}
            user_id: Опциональный UUID пользователя для фильтрации
            include_inactive: Если True, включать неактивные активности
            
        Returns:
            Кортеж (список активностей, общее количество)
        """
        try:
            # Подготавливаем поисковый запрос
            base_query = select(Activity)
            
            # Условия поиска (в названии или в описании)
            search_conditions = [
                Activity.title.ilike(f"%{search_term}%"),
                Activity.description.ilike(f"%{search_term}%")
            ]
            
            # Добавляем фильтр по пользователю
            conditions = [or_(*search_conditions)]
            if user_id:
                conditions.append(Activity.user_id == user_id)
                
            # Добавляем фильтр по активности
            if not include_inactive:
                conditions.append(Activity.is_active == True)
                
            query = base_query.where(and_(*conditions))
            
            # Считаем общее количество
            count_query = select(func.count()).select_from(Activity).where(and_(*conditions))
            count_result = await self.db.execute(count_query)
            total_count = count_result.scalar()
            
            # Применяем сортировку и пагинацию
            query = query.order_by(Activity.start_time.desc())
            
            if pagination:
                skip = pagination.get('skip', 0)
                limit = pagination.get('limit', 100)
                query = query.offset(skip).limit(limit)
            
            result = await self.db.execute(query)
            activities = result.scalars().all()
            
            return activities, total_count
        except Exception as e:
            # Обработка ошибок
            raise e
    
    async def get_activities_by_filters(
        self, 
        filters: Dict[str, Any], 
        pagination: Optional[Dict[str, int]] = None,
        order_by: Optional[List[str]] = None
    ) -> Tuple[List[Activity], int]:
        """
        Получение активностей по сложным фильтрам с поддержкой пагинации.
        
        Args:
            filters: Словарь с условиями фильтрации, поддерживает следующие ключи:
                - user_id: UUID пользователя
                - activity_type_id: UUID типа активности
                - activity_subtype_id: UUID подтипа активности
                - start_date: начальная дата для фильтрации
                - end_date: конечная дата для фильтрации
                - min_priority: минимальный приоритет
                - max_priority: максимальный приоритет
                - is_completed: статус выполнения
                - search_term: поисковый запрос для названия/описания
            pagination: Словарь с параметрами пагинации {'skip': int, 'limit': int}
            order_by: Список полей для сортировки ["field_name", "-field_name"]
            
        Returns:
            Кортеж (список активностей, общее количество)
        """
        try:
            # Подготавливаем базовый запрос
            base_query = select(Activity)
            conditions = []
            
            # Фильтр по пользователю
            if "user_id" in filters:
                conditions.append(Activity.user_id == filters["user_id"])
            
            # Фильтр по типу активности
            if "activity_type_id" in filters:
                conditions.append(Activity.activity_type_id == filters["activity_type_id"])
            
            # Фильтр по подтипу активности
            if "activity_subtype_id" in filters:
                conditions.append(Activity.activity_subtype_id == filters["activity_subtype_id"])
            
            # Фильтр по датам
            if "start_date" in filters:
                conditions.append(Activity.start_time >= filters["start_date"])
            if "end_date" in filters:
                conditions.append(Activity.end_time <= filters["end_date"])
            
            # Фильтр по приоритету
            if "min_priority" in filters:
                conditions.append(Activity.priority >= filters["min_priority"])
            if "max_priority" in filters:
                conditions.append(Activity.priority <= filters["max_priority"])
            
            # Фильтр по статусу выполнения
            if "is_completed" in filters:
                conditions.append(Activity.is_completed == filters["is_completed"])
            
            # Фильтр по активности
            if "is_active" in filters:
                conditions.append(Activity.is_active == filters["is_active"])
            else:
                # По умолчанию показываем только активные
                conditions.append(Activity.is_active == True)
            
            # Поисковый запрос
            if "search_term" in filters and filters["search_term"]:
                search_term = filters["search_term"]
                search_conditions = [
                    Activity.title.ilike(f"%{search_term}%"),
                    Activity.description.ilike(f"%{search_term}%")
                ]
                conditions.append(or_(*search_conditions))
            
            # Теги
            if "tags" in filters and filters["tags"]:
                # Если используется PostgreSQL с поддержкой JSONB
                tags = filters["tags"]
                if isinstance(tags, list):
                    # Проверка наличия всех указанных тегов
                    for tag in tags:
                        # Для PostgreSQL используем оператор @> 
                        # (проверяет, что JSONB содержит указанный элемент)
                        # conditions.append(Activity.tags.contains([tag]))
                        # 
                        # Для SQLite пришлось бы использовать другой подход,
                        # но в данной реализации предполагаем, что используется PostgreSQL
                        conditions.append(Activity.tags.contains([tag]))
            
            # Строим финальный запрос с условиями
            query = base_query.where(and_(*conditions))
            
            # Считаем общее количество
            count_query = select(func.count()).select_from(Activity).where(and_(*conditions))
            count_result = await self.db.execute(count_query)
            total_count = count_result.scalar()
            
            # Применяем сортировку
            if order_by:
                for field_name in order_by:
                    if field_name.startswith('-'):
                        # Сортировка по убыванию
                        field_name = field_name[1:]
                        if hasattr(Activity, field_name):
                            query = query.order_by(getattr(Activity, field_name).desc())
                    else:
                        # Сортировка по возрастанию
                        if hasattr(Activity, field_name):
                            query = query.order_by(getattr(Activity, field_name).asc())
            else:
                # Сортировка по умолчанию - по дате начала (от новых к старым)
                query = query.order_by(Activity.start_time.desc())
            
            # Применяем пагинацию
            if pagination:
                skip = pagination.get('skip', 0)
                limit = pagination.get('limit', 100)
                query = query.offset(skip).limit(limit)
            
            # Выполняем запрос
            result = await self.db.execute(query)
            activities = result.scalars().all()
            
            return activities, total_count
        except Exception as e:
            # Обработка ошибок
            raise e