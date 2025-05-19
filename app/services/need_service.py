"""
Сервис для работы с потребностями.
Реализует бизнес-логику управления потребностями пользователя,
категориями потребностей и историей удовлетворенности.
"""
from typing import List, Optional, Dict, Any, Union, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_, text
from sqlalchemy.orm import joinedload

from app.models.needs import Need, NeedCategory
from app.models.user_needs import UserNeed, UserNeedHistory
from app.modules.need.schemas import (
    UserNeedSatisfactionUpdate, UserNeedHistoryFilter, 
    PaginationParams
)


class NeedRepository:
    """Репозиторий для работы с потребностями"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, need_data: Dict[str, Any]) -> Need:
        """Создание новой потребности"""
        need = Need(**need_data)
        self.db.add(need)
        await self.db.flush()
        await self.db.refresh(need)
        return need
    
    async def get_by_id(self, need_id: UUID) -> Optional[Need]:
        """Получение потребности по ID"""
        query = select(Need).where(Need.id == need_id)
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_by_id_with_category(self, need_id: UUID) -> Optional[Need]:
        """Получение потребности по ID с категорией"""
        query = select(Need).options(joinedload(Need.category)).where(Need.id == need_id)
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def update(self, need_id: UUID, need_data: Dict[str, Any]) -> Optional[Need]:
        """Обновление существующей потребности"""
        query = update(Need).where(Need.id == need_id).values(**need_data).returning(Need)
        result = await self.db.execute(query)
        updated_need = result.scalars().first()
        
        if updated_need:
            await self.db.flush()
            await self.db.refresh(updated_need)
        
        return updated_need
    
    async def delete(self, need_id: UUID) -> bool:
        """Удаление потребности (мягкое удаление через is_active=False)"""
        update_stmt = update(Need).where(Need.id == need_id).values(is_active=False)
        result = await self.db.execute(update_stmt)
        return result.rowcount > 0
    
    async def get_by_user(self, user_id: UUID) -> List[Need]:
        """Получение потребностей пользователя"""
        query = (
            select(Need)
            .options(joinedload(Need.category))
            .where(Need.user_id == user_id, Need.is_active == True)
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_by_category(self, category_id: UUID) -> List[Need]:
        """Получение потребностей для указанной категории"""
        query = (
            select(Need)
            .where(Need.category_id == category_id, Need.is_active == True)
        )
        result = await self.db.execute(query)
        return result.scalars().all()


class NeedCategoryRepository:
    """Репозиторий для работы с категориями потребностей"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_all(self) -> List[NeedCategory]:
        """Получение всех категорий потребностей"""
        query = select(NeedCategory).order_by(NeedCategory.display_order)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_by_id(self, category_id: UUID) -> Optional[NeedCategory]:
        """Получение категории потребностей по ID"""
        query = select(NeedCategory).where(NeedCategory.id == category_id)
        result = await self.db.execute(query)
        return result.scalars().first()


class UserNeedRepository:
    """Репозиторий для работы с потребностями пользователя"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, user_need_data: Dict[str, Any]) -> UserNeed:
        """Создание новой потребности пользователя"""
        user_need = UserNeed(**user_need_data)
        self.db.add(user_need)
        await self.db.flush()
        await self.db.refresh(user_need)
        return user_need
    
    async def get_by_id(self, user_need_id: UUID) -> Optional[UserNeed]:
        """Получение потребности пользователя по ID"""
        query = select(UserNeed).where(UserNeed.id == user_need_id)
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_by_id_with_relations(self, user_need_id: UUID) -> Optional[UserNeed]:
        """Получение потребности пользователя по ID со связанными данными"""
        query = (
            select(UserNeed)
            .options(
                joinedload(UserNeed.need).joinedload(Need.category)
            )
            .where(UserNeed.id == user_need_id)
        )
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_by_user_and_need(self, user_id: UUID, need_id: UUID) -> Optional[UserNeed]:
        """Получение потребности пользователя по ID пользователя и ID потребности"""
        query = (
            select(UserNeed)
            .where(UserNeed.user_id == user_id, UserNeed.need_id == need_id)
        )
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def update(self, user_need_id: UUID, user_need_data: Dict[str, Any]) -> Optional[UserNeed]:
        """Обновление существующей потребности пользователя"""
        query = update(UserNeed).where(UserNeed.id == user_need_id).values(**user_need_data).returning(UserNeed)
        result = await self.db.execute(query)
        updated_user_need = result.scalars().first()
        
        if updated_user_need:
            await self.db.flush()
            await self.db.refresh(updated_user_need)
        
        return updated_user_need
    
    async def delete(self, user_need_id: UUID) -> bool:
        """Удаление потребности пользователя (мягкое удаление через is_active=False)"""
        update_stmt = update(UserNeed).where(UserNeed.id == user_need_id).values(is_active=False)
        result = await self.db.execute(update_stmt)
        return result.rowcount > 0
    
    async def get_by_user(self, user_id: UUID) -> List[UserNeed]:
        """Получение всех потребностей пользователя"""
        query = (
            select(UserNeed)
            .options(
                joinedload(UserNeed.need).joinedload(Need.category)
            )
            .where(UserNeed.user_id == user_id, UserNeed.is_active == True)
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_requiring_attention(self, user_id: UUID, threshold: float) -> List[UserNeed]:
        """Получение потребностей, требующих внимания (низкий уровень удовлетворенности)"""
        query = (
            select(UserNeed)
            .options(
                joinedload(UserNeed.need).joinedload(Need.category)
            )
            .where(
                UserNeed.user_id == user_id,
                UserNeed.is_active == True,
                UserNeed.current_satisfaction <= threshold
            )
            .order_by(UserNeed.current_satisfaction)
        )
        result = await self.db.execute(query)
        return result.scalars().all()


class UserNeedHistoryRepository:
    """Репозиторий для работы с историей потребностей пользователя"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, history_data: Dict[str, Any]) -> UserNeedHistory:
        """Создание новой записи в истории потребностей"""
        history = UserNeedHistory(**history_data)
        self.db.add(history)
        await self.db.flush()
        await self.db.refresh(history)
        return history
    
    async def get_by_id(self, history_id: UUID) -> Optional[UserNeedHistory]:
        """Получение записи истории по ID"""
        query = select(UserNeedHistory).where(UserNeedHistory.id == history_id)
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_filtered(
        self, 
        user_id: UUID,
        need_id: Optional[UUID] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        context: Optional[str] = None,
        pagination: Dict[str, Any] = None
    ) -> Tuple[List[UserNeedHistory], int]:
        """Получение отфильтрованной истории потребностей с общим количеством"""
        # Базовый запрос
        query = select(UserNeedHistory).where(UserNeedHistory.user_id == user_id)
        
        # Применение фильтров
        if need_id:
            query = query.where(UserNeedHistory.need_id == need_id)
        
        if from_date:
            query = query.where(UserNeedHistory.timestamp >= from_date)
        
        if to_date:
            query = query.where(UserNeedHistory.timestamp <= to_date)
        
        if context:
            query = query.where(UserNeedHistory.context == context)
        
        # Подсчет общего количества
        count_query = select(func.count()).select_from(query.subquery())
        total_count = await self.db.execute(count_query)
        total_count = total_count.scalar() or 0
        
        # Применение сортировки и пагинации
        if pagination:
            sort_field = getattr(UserNeedHistory, pagination.get("sort_by", "timestamp"))
            sort_dir = sort_field.desc() if pagination.get("sort_desc", True) else sort_field.asc()
            
            query = (
                query
                .order_by(sort_dir)
                .offset((pagination["page"] - 1) * pagination["per_page"])
                .limit(pagination["per_page"])
            )
        else:
            # По умолчанию сортируем по времени (сначала новые)
            query = query.order_by(UserNeedHistory.timestamp.desc())
        
        # Выполнение запроса
        result = await self.db.execute(query)
        history_entries = result.scalars().all()
        
        return history_entries, total_count


class NeedService:
    """Сервис для работы с потребностями"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.need_repository = NeedRepository(db)
        self.need_category_repository = NeedCategoryRepository(db)
        self.user_need_repository = UserNeedRepository(db)
        self.user_need_history_repository = UserNeedHistoryRepository(db)
    
    async def get_need_categories(self) -> List[NeedCategory]:
        """Получение всех категорий потребностей"""
        return await self.need_category_repository.get_all()
    
    async def get_needs_by_category(self, category_id: UUID) -> List[Need]:
        """Получение потребностей для указанной категории"""
        category = await self.need_category_repository.get_by_id(category_id)
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Need category with ID {category_id} not found"
            )
        
        return await self.need_repository.get_by_category(category_id)
    
    async def get_user_needs(self, user_id: UUID) -> List[UserNeed]:
        """Получение всех потребностей пользователя"""
        return await self.user_need_repository.get_by_user(user_id)
    
    async def get_user_need_by_id(self, user_need_id: UUID, user_id: UUID) -> UserNeed:
        """Получение потребности пользователя по ID"""
        user_need = await self.user_need_repository.get_by_id_with_relations(user_need_id)
        
        if not user_need:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User need with ID {user_need_id} not found"
            )
        
        # Проверка прав доступа
        if user_need.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this user need"
            )
        
        return user_need
    
    async def update_user_need_satisfaction(
        self, 
        user_id: UUID, 
        need_id: UUID, 
        satisfaction_update: UserNeedSatisfactionUpdate
    ) -> Tuple[UserNeed, UserNeedHistory]:
        """Обновление уровня удовлетворенности потребности"""
        # Получаем потребность пользователя
        user_need = await self.user_need_repository.get_by_user_and_need(user_id, need_id)
        
        if not user_need:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User need with need_id {need_id} for user {user_id} not found"
            )
        
        # Обновляем уровень удовлетворенности и создаем запись в истории
        old_value = user_need.current_satisfaction
        user_need.current_satisfaction = max(-5.0, min(5.0, satisfaction_update.satisfaction_level))
        
        # Создаем запись в истории
        history_data = {
            "user_need_id": user_need.id,
            "user_id": user_id,
            "need_id": need_id,
            "satisfaction_level": user_need.current_satisfaction,
            "previous_value": old_value,
            "change_value": user_need.current_satisfaction - old_value,
            "context": satisfaction_update.context,
            "note": satisfaction_update.note
        }
        
        # Обновляем потребность пользователя
        update_data = {"current_satisfaction": user_need.current_satisfaction}
        await self.user_need_repository.update(user_need.id, update_data)
        
        # Создаем запись в истории
        history_entry = await self.user_need_history_repository.create(history_data)
        
        return user_need, history_entry
    
    async def record_need_history(
        self, 
        user_id: UUID, 
        need_id: UUID, 
        satisfaction_level: float, 
        context: Optional[str] = None,
        note: Optional[str] = None,
        activity_id: Optional[UUID] = None
    ) -> UserNeedHistory:
        """Запись истории уровня удовлетворенности потребности"""
        # Получаем потребность пользователя
        user_need = await self.user_need_repository.get_by_user_and_need(user_id, need_id)
        
        if not user_need:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User need with need_id {need_id} for user {user_id} not found"
            )
        
        # Создаем запись в истории
        history_data = {
            "user_need_id": user_need.id,
            "user_id": user_id,
            "need_id": need_id,
            "satisfaction_level": max(-5.0, min(5.0, satisfaction_level)),
            "previous_value": user_need.current_satisfaction,
            "change_value": satisfaction_level - user_need.current_satisfaction,
            "context": context,
            "note": note,
            "activity_id": activity_id
        }
        
        # Создаем запись в истории
        history_entry = await self.user_need_history_repository.create(history_data)
        
        return history_entry
    
    async def get_need_history(
        self, 
        user_id: UUID, 
        filter_params: UserNeedHistoryFilter,
        pagination: PaginationParams
    ) -> Tuple[List[UserNeedHistory], int]:
        """Получение истории удовлетворенности потребностей"""
        pagination_dict = pagination.dict(exclude_unset=True)
        
        return await self.user_need_history_repository.get_filtered(
            user_id=user_id,
            need_id=filter_params.need_id,
            from_date=filter_params.from_date,
            to_date=filter_params.to_date,
            context=filter_params.context,
            pagination=pagination_dict
        )
    
    async def get_needs_requiring_attention(self, user_id: UUID, threshold: float = -2.0) -> List[UserNeed]:
        """Получение потребностей, требующих внимания (низкий уровень удовлетворенности)"""
        return await self.user_need_repository.get_requiring_attention(user_id, threshold)
    
    async def calculate_overall_needs_satisfaction(self, user_id: UUID) -> float:
        """Расчет общего уровня удовлетворенности потребностей"""
        user_needs = await self.get_user_needs(user_id)
        
        if not user_needs:
            return 0.0
        
        # Считаем взвешенное среднее, учитывая важность каждой потребности
        total_satisfaction = 0.0
        total_importance = 0.0
        
        for user_need in user_needs:
            total_satisfaction += user_need.current_satisfaction * user_need.importance
            total_importance += user_need.importance
        
        if total_importance == 0:
            return 0.0
        
        # Нормализуем результат к диапазону 0-100%
        # Преобразуем из шкалы -5..5 в 0..10, затем в процентное отношение
        result = total_satisfaction / total_importance
        normalized_result = (result + 5) / 10
        
        return normalized_result * 100
    
    async def get_need_satisfaction_trends(
        self, 
        user_id: UUID, 
        days: int = 7
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Получение трендов удовлетворенности потребностей за указанный период"""
        now = datetime.now()
        from_date = now - timedelta(days=days)
        
        # Получаем историю удовлетворенности потребностей за указанный период
        filter_params = UserNeedHistoryFilter(from_date=from_date)
        pagination = PaginationParams(page=1, per_page=1000, sort_by="timestamp", sort_desc=False)
        
        history_entries, _ = await self.get_need_history(user_id, filter_params, pagination)
        
        # Группируем записи по потребностям
        need_history: Dict[UUID, List[Dict[str, Any]]] = {}
        
        for entry in history_entries:
            if entry.need_id not in need_history:
                need_history[entry.need_id] = []
            
            need_history[entry.need_id].append({
                "timestamp": entry.timestamp,
                "satisfaction_level": entry.satisfaction_level,
                "context": entry.context
            })
        
        # Дополняем информацией о потребностях
        user_needs = await self.get_user_needs(user_id)
        user_needs_dict = {user_need.need_id: user_need for user_need in user_needs}
        
        result = {}
        for need_id, history in need_history.items():
            if need_id in user_needs_dict:
                user_need = user_needs_dict[need_id]
                need_name = user_need.custom_name or user_need.need.name
                result[need_name] = history
        
        return result