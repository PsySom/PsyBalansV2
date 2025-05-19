"""
Репозиторий для работы с календарями пользователей.
"""
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, text
from sqlalchemy.sql import Select
from sqlalchemy.orm import joinedload
from uuid import UUID

from app.models.calendar import UserCalendar, ActivitySchedule
from app.repositories.base_repository import BaseRepository


class CalendarRepository(BaseRepository[UserCalendar]):
    """
    Репозиторий для работы с календарями пользователей.
    Предоставляет методы для управления календарями и
    проверки связанных условий.
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Инициализация репозитория с сессией базы данных.
        
        Args:
            db_session: Асинхронная сессия SQLAlchemy
        """
        super().__init__(db_session, UserCalendar)
    
    async def create_calendar(self, calendar_data: Dict[str, Any]) -> UserCalendar:
        """
        Создание нового календаря пользователя.
        
        Args:
            calendar_data: Данные для создания календаря
            
        Returns:
            Созданный календарь
        """
        user_id = calendar_data.get("user_id")
        
        # Проверяем наличие других календарей пользователя
        has_calendars = await self.has_user_calendars(user_id)
        
        # Если это первый календарь, он автоматически становится основным и по умолчанию
        if not has_calendars:
            calendar_data["is_primary"] = True
            calendar_data["is_default"] = True
        
        # Если пользователь устанавливает этот календарь как основной, сбрасываем флаг у других
        if calendar_data.get("is_primary"):
            await self._reset_primary_flag(user_id)
        
        # Если пользователь устанавливает этот календарь как календарь по умолчанию, сбрасываем флаг у других
        if calendar_data.get("is_default"):
            await self._reset_default_flag(user_id)
        
        # Создаем календарь
        calendar = await self.create(calendar_data)
        return calendar
    
    async def get_user_calendars(
        self, 
        user_id: UUID, 
        active_only: bool = True,
        include_shared: bool = False
    ) -> List[UserCalendar]:
        """
        Получение всех календарей пользователя.
        
        Args:
            user_id: Идентификатор пользователя
            active_only: Флаг для фильтрации только активных календарей
            include_shared: Флаг для включения общих календарей
            
        Returns:
            Список календарей пользователя
        """
        query = select(self.model).where(self.model.user_id == user_id)
        
        if active_only:
            query = query.where(self.model.is_active == True)
        
        if include_shared:
            # Добавляем общие календари других пользователей
            shared_query = select(self.model).where(
                self.model.is_shared == True,
                self.model.user_id != user_id,
                self.model.is_active == True
            )
            # Объединяем запросы
            query = query.union(shared_query)
        
        # Сортируем по порядку отображения и флагу основного календаря
        query = query.order_by(self.model.is_primary.desc(), self.model.display_order)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_primary_calendar(self, user_id: UUID) -> Optional[UserCalendar]:
        """
        Получение основного календаря пользователя.
        
        Args:
            user_id: Идентификатор пользователя
            
        Returns:
            Основной календарь или None, если не найден
        """
        query = select(self.model).where(
            self.model.user_id == user_id,
            self.model.is_primary == True,
            self.model.is_active == True
        )
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_default_calendar(self, user_id: UUID) -> Optional[UserCalendar]:
        """
        Получение календаря по умолчанию пользователя.
        
        Args:
            user_id: Идентификатор пользователя
            
        Returns:
            Календарь по умолчанию или None, если не найден
        """
        query = select(self.model).where(
            self.model.user_id == user_id,
            self.model.is_default == True,
            self.model.is_active == True
        )
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def update_calendar(self, calendar_id: UUID, calendar_data: Dict[str, Any]) -> Optional[UserCalendar]:
        """
        Обновление настроек календаря.
        
        Args:
            calendar_id: Идентификатор календаря
            calendar_data: Данные для обновления
            
        Returns:
            Обновленный календарь или None, если не найден
        """
        # Получаем текущий календарь
        calendar = await self.get_by_id(calendar_id)
        if not calendar:
            return None
        
        # Если пользователь устанавливает этот календарь как основной, сбрасываем флаг у других
        if calendar_data.get("is_primary"):
            await self._reset_primary_flag(calendar.user_id)
        
        # Если пользователь устанавливает этот календарь как календарь по умолчанию, сбрасываем флаг у других
        if calendar_data.get("is_default"):
            await self._reset_default_flag(calendar.user_id)
        
        # Выполняем обновление
        updated_calendar = await self.update(calendar_id, calendar_data)
        return updated_calendar
    
    async def delete_calendar(self, calendar_id: UUID) -> bool:
        """
        Мягкое удаление календаря.
        
        Args:
            calendar_id: Идентификатор календаря
            
        Returns:
            True если удаление успешно, иначе False
        """
        # Получаем текущий календарь
        calendar = await self.get_by_id(calendar_id)
        if not calendar:
            return False
        
        # Проверяем наличие других активных календарей
        other_calendars = await self._get_other_active_calendars(calendar.user_id, calendar_id)
        
        # Если это единственный календарь, запрещаем удаление
        if not other_calendars:
            return False
        
        # Если это основной календарь или календарь по умолчанию,
        # нужно назначить другой календарь как основной/по умолчанию
        if calendar.is_primary or calendar.is_default:
            # Берем первый другой активный календарь
            other_calendar = other_calendars[0]
            update_data = {}
            
            if calendar.is_primary:
                update_data["is_primary"] = True
            
            if calendar.is_default:
                update_data["is_default"] = True
            
            await self.update(other_calendar.id, update_data)
        
        # Выполняем мягкое удаление
        result = await self.delete(calendar_id, soft_delete=True)
        return result
    
    async def has_user_calendars(self, user_id: UUID) -> bool:
        """
        Проверка наличия у пользователя хотя бы одного календаря.
        
        Args:
            user_id: Идентификатор пользователя
            
        Returns:
            True если у пользователя есть хотя бы один календарь, иначе False
        """
        query = select(func.count(self.model.id)).where(
            self.model.user_id == user_id,
            self.model.is_active == True
        )
        result = await self.db.execute(query)
        count = result.scalar()
        return count > 0
    
    async def has_user_active_calendars(self, user_id: UUID) -> bool:
        """
        Проверка наличия у пользователя хотя бы одного активного календаря.
        
        Args:
            user_id: Идентификатор пользователя
            
        Returns:
            True если у пользователя есть хотя бы один активный календарь, иначе False
        """
        query = select(func.count(self.model.id)).where(
            self.model.user_id == user_id,
            self.model.is_active == True
        )
        result = await self.db.execute(query)
        count = result.scalar()
        return count > 0
    
    async def ensure_primary_calendar(self, user_id: UUID) -> Optional[UserCalendar]:
        """
        Проверка наличия основного календаря у пользователя.
        Если основного календаря нет, назначает первый активный календарь основным.
        
        Args:
            user_id: Идентификатор пользователя
            
        Returns:
            Основной календарь или None, если у пользователя нет календарей
        """
        # Проверяем наличие основного календаря
        primary_calendar = await self.get_primary_calendar(user_id)
        
        if primary_calendar:
            return primary_calendar
        
        # Если основного календаря нет, ищем первый активный
        query = select(self.model).where(
            self.model.user_id == user_id,
            self.model.is_active == True
        ).order_by(self.model.created_at)
        
        result = await self.db.execute(query)
        first_calendar = result.scalars().first()
        
        if first_calendar:
            # Назначаем его основным
            await self.update(first_calendar.id, {"is_primary": True})
            return await self.get_by_id(first_calendar.id)
        
        return None
    
    async def ensure_default_calendar(self, user_id: UUID) -> Optional[UserCalendar]:
        """
        Проверка наличия календаря по умолчанию у пользователя.
        Если календаря по умолчанию нет, назначает первый активный календарь календарем по умолчанию.
        
        Args:
            user_id: Идентификатор пользователя
            
        Returns:
            Календарь по умолчанию или None, если у пользователя нет календарей
        """
        # Проверяем наличие календаря по умолчанию
        default_calendar = await self.get_default_calendar(user_id)
        
        if default_calendar:
            return default_calendar
        
        # Если календаря по умолчанию нет, ищем первый активный
        query = select(self.model).where(
            self.model.user_id == user_id,
            self.model.is_active == True
        ).order_by(self.model.created_at)
        
        result = await self.db.execute(query)
        first_calendar = result.scalars().first()
        
        if first_calendar:
            # Назначаем его календарем по умолчанию
            await self.update(first_calendar.id, {"is_default": True})
            return await self.get_by_id(first_calendar.id)
        
        return None
    
    async def get_calendar_with_schedules(self, calendar_id: UUID) -> Optional[UserCalendar]:
        """
        Получение календаря вместе со связанными расписаниями.
        
        Args:
            calendar_id: Идентификатор календаря
            
        Returns:
            Календарь со связанными расписаниями или None, если не найден
        """
        query = (
            select(self.model)
            .where(self.model.id == calendar_id)
            .options(joinedload(self.model.schedules))
        )
        result = await self.db.execute(query)
        return result.scalars().first()
    
    # Вспомогательные методы
    
    async def _reset_primary_flag(self, user_id: UUID) -> None:
        """
        Сбрасывает флаг основного календаря у всех календарей пользователя.
        
        Args:
            user_id: Идентификатор пользователя
        """
        query = (
            text("UPDATE user_calendars SET is_primary = FALSE "
                 "WHERE user_id = :user_id")
        )
        await self.db.execute(query, {"user_id": user_id})
    
    async def _reset_default_flag(self, user_id: UUID) -> None:
        """
        Сбрасывает флаг календаря по умолчанию у всех календарей пользователя.
        
        Args:
            user_id: Идентификатор пользователя
        """
        query = (
            text("UPDATE user_calendars SET is_default = FALSE "
                 "WHERE user_id = :user_id")
        )
        await self.db.execute(query, {"user_id": user_id})
    
    async def _get_other_active_calendars(self, user_id: UUID, exclude_id: UUID) -> List[UserCalendar]:
        """
        Получение списка других активных календарей пользователя, исключая указанный.
        
        Args:
            user_id: Идентификатор пользователя
            exclude_id: Идентификатор календаря для исключения
            
        Returns:
            Список других активных календарей
        """
        query = select(self.model).where(
            self.model.user_id == user_id,
            self.model.id != exclude_id,
            self.model.is_active == True
        )
        result = await self.db.execute(query)
        return result.scalars().all()