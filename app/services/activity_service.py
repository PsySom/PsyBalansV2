"""
Сервис для работы с активностями.
Реализует бизнес-логику управления активностями пользователя, 
типами активностей и их связями с потребностями.
"""
from typing import List, Optional, Dict, Any, Union, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_, text
from sqlalchemy.orm import joinedload

from app.models.activity import Activity, ActivityEvaluation, ActivityNeed
from app.models.activity_types import ActivityType, ActivitySubtype
from app.models.needs import Need
from app.modules.activity.schemas import (
    ActivityCreate, ActivityUpdate, ActivityFilter,
    PaginationParams, ActivityNeedLinkCreate
)


class ActivityRepository:
    """Репозиторий для работы с активностями в базе данных"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, activity_data: Dict[str, Any]) -> Activity:
        """Создание новой активности"""
        activity = Activity(**activity_data)
        self.db.add(activity)
        await self.db.flush()
        await self.db.refresh(activity)
        return activity
    
    async def get_by_id(self, activity_id: UUID) -> Optional[Activity]:
        """Получение активности по ID"""
        query = select(Activity).where(Activity.id == activity_id)
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_by_id_with_relations(self, activity_id: UUID) -> Optional[Activity]:
        """Получение активности по ID со связанными объектами"""
        query = (
            select(Activity)
            .options(
                joinedload(Activity.activity_type),
                joinedload(Activity.activity_subtype),
                joinedload(Activity.activity_needs).joinedload(ActivityNeed.need),
                joinedload(Activity.evaluations)
            )
            .where(Activity.id == activity_id)
        )
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def update(self, activity_id: UUID, activity_data: Dict[str, Any]) -> Optional[Activity]:
        """Обновление существующей активности"""
        query = update(Activity).where(Activity.id == activity_id).values(**activity_data).returning(Activity)
        result = await self.db.execute(query)
        updated_activity = result.scalars().first()
        
        if updated_activity:
            await self.db.flush()
            await self.db.refresh(updated_activity)
        
        return updated_activity
    
    async def delete(self, activity_id: UUID) -> bool:
        """Удаление активности (мягкое удаление через is_active=False)"""
        update_stmt = update(Activity).where(Activity.id == activity_id).values(is_active=False)
        result = await self.db.execute(update_stmt)
        return result.rowcount > 0
    
    async def get_filtered(
        self, 
        user_id: UUID,
        filters: Dict[str, Any], 
        pagination: Dict[str, Any]
    ) -> Tuple[List[Activity], int]:
        """Получение отфильтрованного списка активностей с общим количеством"""
        # Базовый запрос
        query = select(Activity).where(Activity.user_id == user_id)
        
        # Применение фильтров
        if filters.get("start_date"):
            query = query.where(Activity.start_time >= filters["start_date"])
        
        if filters.get("end_date"):
            query = query.where(Activity.start_time <= filters["end_date"])
        
        if filters.get("is_completed") is not None:
            query = query.where(Activity.is_completed == filters["is_completed"])
        
        if filters.get("activity_type_id"):
            query = query.where(Activity.activity_type_id == filters["activity_type_id"])
        
        if filters.get("activity_subtype_id"):
            query = query.where(Activity.activity_subtype_id == filters["activity_subtype_id"])
        
        if filters.get("priority"):
            query = query.where(Activity.priority == filters["priority"])
        
        # Подсчет общего количества
        count_query = select(func.count()).select_from(query.subquery())
        total_count = await self.db.execute(count_query)
        total_count = total_count.scalar() or 0
        
        # Применение сортировки и пагинации
        sort_field = getattr(Activity, pagination.get("sort_by", "start_time"))
        sort_dir = sort_field.desc() if pagination.get("sort_desc", True) else sort_field.asc()
        
        query = (
            query
            .order_by(sort_dir)
            .offset((pagination["page"] - 1) * pagination["per_page"])
            .limit(pagination["per_page"])
        )
        
        # Выполнение запроса
        result = await self.db.execute(query)
        activities = result.scalars().all()
        
        return activities, total_count
    
    async def link_to_need(self, link_data: Dict[str, Any]) -> ActivityNeed:
        """Связывание активности с потребностью"""
        # Проверяем, существует ли уже такая связь
        query = select(ActivityNeed).where(
            ActivityNeed.activity_id == link_data["activity_id"],
            ActivityNeed.need_id == link_data["need_id"]
        )
        result = await self.db.execute(query)
        existing_link = result.scalars().first()
        
        if existing_link:
            # Обновляем существующую связь
            for key, value in link_data.items():
                setattr(existing_link, key, value)
            await self.db.flush()
            await self.db.refresh(existing_link)
            return existing_link
        else:
            # Создаем новую связь
            link = ActivityNeed(**link_data)
            self.db.add(link)
            await self.db.flush()
            await self.db.refresh(link)
            return link
    
    async def get_need_links(self, activity_id: UUID) -> List[ActivityNeed]:
        """Получение связей активности с потребностями"""
        query = (
            select(ActivityNeed)
            .options(joinedload(ActivityNeed.need))
            .where(ActivityNeed.activity_id == activity_id)
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def update_need_link(
        self, 
        activity_id: UUID,
        need_id: UUID,
        update_data: Dict[str, Any]
    ) -> Optional[ActivityNeed]:
        """Обновление связи активности с потребностью"""
        query = (
            update(ActivityNeed)
            .where(
                ActivityNeed.activity_id == activity_id,
                ActivityNeed.need_id == need_id
            )
            .values(**update_data)
            .returning(ActivityNeed)
        )
        result = await self.db.execute(query)
        updated_link = result.scalars().first()
        
        if updated_link:
            await self.db.flush()
            await self.db.refresh(updated_link)
        
        return updated_link
    
    async def delete_need_link(self, activity_id: UUID, need_id: UUID) -> bool:
        """Удаление связи активности с потребностью"""
        query = delete(ActivityNeed).where(
            ActivityNeed.activity_id == activity_id,
            ActivityNeed.need_id == need_id
        )
        result = await self.db.execute(query)
        return result.rowcount > 0


class ActivityTypeRepository:
    """Репозиторий для работы с типами активностей"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_all(self) -> List[ActivityType]:
        """Получение всех типов активностей"""
        query = select(ActivityType)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_by_id(self, type_id: UUID) -> Optional[ActivityType]:
        """Получение типа активности по ID"""
        query = select(ActivityType).where(ActivityType.id == type_id)
        result = await self.db.execute(query)
        return result.scalars().first()


class ActivitySubtypeRepository:
    """Репозиторий для работы с подтипами активностей"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_all(self) -> List[ActivitySubtype]:
        """Получение всех подтипов активностей"""
        query = select(ActivitySubtype)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_by_id(self, subtype_id: UUID) -> Optional[ActivitySubtype]:
        """Получение подтипа активности по ID"""
        query = select(ActivitySubtype).where(ActivitySubtype.id == subtype_id)
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_by_type(self, type_id: UUID) -> List[ActivitySubtype]:
        """Получение подтипов для указанного типа активности"""
        query = select(ActivitySubtype).where(ActivitySubtype.activity_type_id == type_id)
        result = await self.db.execute(query)
        return result.scalars().all()


class ActivityService:
    """Сервис для работы с активностями"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.activity_repository = ActivityRepository(db)
        self.activity_type_repository = ActivityTypeRepository(db)
        self.activity_subtype_repository = ActivitySubtypeRepository(db)
    
    async def create_activity(self, activity_data: ActivityCreate, user_id: UUID) -> Activity:
        """Создание новой активности"""
        try:
            activity_dict = activity_data.dict(exclude_unset=True, exclude={"user_id"})
            activity_dict["user_id"] = user_id
            
            # Рассчитать длительность в минутах
            if "start_time" in activity_dict and "end_time" in activity_dict:
                delta = activity_dict["end_time"] - activity_dict["start_time"]
                activity_dict["duration_minutes"] = int(delta.total_seconds() / 60)
            
            # Проверить существование типа и подтипа активности, если указаны
            if activity_dict.get("activity_type_id"):
                activity_type = await self.activity_type_repository.get_by_id(activity_dict["activity_type_id"])
                if not activity_type:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"ActivityType with ID {activity_dict['activity_type_id']} not found"
                    )
            
            if activity_dict.get("activity_subtype_id"):
                activity_subtype = await self.activity_subtype_repository.get_by_id(activity_dict["activity_subtype_id"])
                if not activity_subtype:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"ActivitySubtype with ID {activity_dict['activity_subtype_id']} not found"
                    )
                
                # Проверить, соответствует ли подтип указанному типу
                if activity_dict.get("activity_type_id") and activity_subtype.activity_type_id != activity_dict["activity_type_id"]:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"ActivitySubtype with ID {activity_dict['activity_subtype_id']} does not belong to ActivityType with ID {activity_dict['activity_type_id']}"
                    )
            
            return await self.activity_repository.create(activity_dict)
        except Exception as e:
            if "check_end_time_after_start_time" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="End time must be after start time"
                )
            raise
    
    async def get_activity_by_id(self, activity_id: UUID, user_id: UUID) -> Activity:
        """Получение активности по ID"""
        activity = await self.activity_repository.get_by_id_with_relations(activity_id)
        
        if not activity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Activity with ID {activity_id} not found"
            )
        
        # Проверка прав доступа
        if activity.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this activity"
            )
        
        return activity
    
    async def update_activity(self, activity_id: UUID, activity_data: ActivityUpdate, user_id: UUID) -> Activity:
        """Обновление существующей активности"""
        # Получаем существующую активность
        activity = await self.activity_repository.get_by_id(activity_id)
        
        if not activity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Activity with ID {activity_id} not found"
            )
        
        # Проверка прав доступа
        if activity.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this activity"
            )
        
        # Подготовка данных для обновления
        update_data = activity_data.dict(exclude_unset=True)
        
        # Обновляем duration_minutes, если изменились start_time или end_time
        start_time = update_data.get("start_time", activity.start_time)
        end_time = update_data.get("end_time", activity.end_time)
        
        # Проверка, что end_time > start_time
        if end_time <= start_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End time must be after start time"
            )
        
        if "start_time" in update_data or "end_time" in update_data:
            delta = end_time - start_time
            update_data["duration_minutes"] = int(delta.total_seconds() / 60)
        
        # Если активность помечается как выполненная, устанавливаем время выполнения
        if update_data.get("is_completed", False) and not activity.is_completed:
            update_data["completion_time"] = datetime.now()
        
        # Обновляем активность
        updated_activity = await self.activity_repository.update(activity_id, update_data)
        
        if not updated_activity:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update activity"
            )
        
        return updated_activity
    
    async def delete_activity(self, activity_id: UUID, user_id: UUID) -> bool:
        """Удаление активности (мягкое удаление через is_active=False)"""
        # Получаем существующую активность
        activity = await self.activity_repository.get_by_id(activity_id)
        
        if not activity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Activity with ID {activity_id} not found"
            )
        
        # Проверка прав доступа
        if activity.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this activity"
            )
        
        # Мягкое удаление
        success = await self.activity_repository.delete(activity_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete activity"
            )
        
        return True
    
    async def get_activities(
        self, 
        user_id: UUID, 
        filters: ActivityFilter, 
        pagination: PaginationParams
    ) -> Tuple[List[Activity], int]:
        """Получение списка активностей с фильтрацией и пагинацией"""
        filters_dict = filters.dict(exclude_unset=True)
        pagination_dict = pagination.dict(exclude_unset=True)
        
        return await self.activity_repository.get_filtered(user_id, filters_dict, pagination_dict)
    
    async def get_activity_types(self) -> List[ActivityType]:
        """Получение всех типов активностей"""
        return await self.activity_type_repository.get_all()
    
    async def get_subtypes_by_type(self, type_id: UUID) -> List[ActivitySubtype]:
        """Получение подтипов для указанного типа активности"""
        activity_type = await self.activity_type_repository.get_by_id(type_id)
        
        if not activity_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ActivityType with ID {type_id} not found"
            )
        
        return await self.activity_subtype_repository.get_by_type(type_id)
    
    async def link_activity_to_needs(
        self, 
        activity_id: UUID, 
        need_links: List[ActivityNeedLinkCreate], 
        user_id: UUID
    ) -> bool:
        """Связывание активности с потребностями"""
        # Получаем существующую активность
        activity = await self.activity_repository.get_by_id(activity_id)
        
        if not activity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Activity with ID {activity_id} not found"
            )
        
        # Проверка прав доступа
        if activity.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to modify this activity"
            )
        
        # Создаем связи с потребностями
        for link_data in need_links:
            link_dict = link_data.dict(exclude_unset=True)
            link_dict["activity_id"] = activity_id
            
            try:
                await self.activity_repository.link_to_need(link_dict)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to link activity to need: {str(e)}"
                )
        
        return True
    
    async def get_activity_need_links(self, activity_id: UUID, user_id: UUID) -> List[ActivityNeed]:
        """Получение связей активности с потребностями"""
        # Получаем существующую активность
        activity = await self.activity_repository.get_by_id(activity_id)
        
        if not activity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Activity with ID {activity_id} not found"
            )
        
        # Проверка прав доступа
        if activity.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this activity"
            )
        
        return await self.activity_repository.get_need_links(activity_id)
    
    async def update_activity_need_link(
        self, 
        activity_id: UUID, 
        need_id: UUID, 
        update_data: Dict[str, Any], 
        user_id: UUID
    ) -> ActivityNeed:
        """Обновление связи активности с потребностью"""
        # Получаем существующую активность
        activity = await self.activity_repository.get_by_id(activity_id)
        
        if not activity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Activity with ID {activity_id} not found"
            )
        
        # Проверка прав доступа
        if activity.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to modify this activity"
            )
        
        # Обновляем связь
        updated_link = await self.activity_repository.update_need_link(activity_id, need_id, update_data)
        
        if not updated_link:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Link between activity {activity_id} and need {need_id} not found"
            )
        
        return updated_link
    
    async def delete_activity_need_link(
        self, 
        activity_id: UUID, 
        need_id: UUID, 
        user_id: UUID
    ) -> bool:
        """Удаление связи активности с потребностью"""
        # Получаем существующую активность
        activity = await self.activity_repository.get_by_id(activity_id)
        
        if not activity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Activity with ID {activity_id} not found"
            )
        
        # Проверка прав доступа
        if activity.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to modify this activity"
            )
        
        # Удаляем связь
        success = await self.activity_repository.delete_need_link(activity_id, need_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Link between activity {activity_id} and need {need_id} not found"
            )
        
        return True
    
    async def get_upcoming_activities(self, user_id: UUID, days: int = 7) -> List[Activity]:
        """Получение предстоящих активностей пользователя"""
        now = datetime.now()
        end_date = now + timedelta(days=days)
        
        filters = ActivityFilter(
            start_date=now,
            end_date=end_date,
            is_completed=False
        )
        pagination = PaginationParams(page=1, per_page=100, sort_by="start_time", sort_desc=False)
        
        activities, _ = await self.get_activities(user_id, filters, pagination)
        return activities
    
    async def get_overdue_activities(self, user_id: UUID) -> List[Activity]:
        """Получение просроченных активностей пользователя"""
        now = datetime.now()
        
        filters_dict = {
            "end_date": now,
            "is_completed": False
        }
        pagination_dict = {
            "page": 1,
            "per_page": 100,
            "sort_by": "end_time",
            "sort_desc": True
        }
        
        activities, _ = await self.activity_repository.get_filtered(user_id, filters_dict, pagination_dict)
        return [activity for activity in activities if activity.is_overdue]