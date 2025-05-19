"""
Репозиторий для работы с связями между активностями и потребностями.
"""
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError

from app.repositories.base_repository import BaseRepository
from app.models.activity import ActivityNeed, Activity
from app.models.needs import Need


class ActivityNeedLinkRepository(BaseRepository):
    """
    Репозиторий для работы с связями между активностями и потребностями.
    Реализует методы для создания, обновления, удаления и поиска связей.
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Инициализация репозитория.
        
        Args:
            db_session: Асинхронная сессия базы данных
        """
        super().__init__(db_session, ActivityNeed)
    
    async def get_needs_for_activity(self, activity_id: UUID) -> Tuple[List[ActivityNeed], bool]:
        """
        Получение потребностей, связанных с активностью.
        
        Args:
            activity_id: Идентификатор активности
            
        Returns:
            Кортеж из списка связей активности с потребностями и флага существования активности
        """
        # Проверяем существование активности
        activity_exists = await self._check_activity_exists(activity_id)
        
        if not activity_exists:
            return [], False
        
        query = (
            select(ActivityNeed)
            .options(joinedload(ActivityNeed.need))
            .where(ActivityNeed.activity_id == activity_id)
        )
        result = await self.db.execute(query)
        return result.scalars().all(), True
    
    async def get_activities_for_need(self, need_id: UUID) -> Tuple[List[ActivityNeed], bool]:
        """
        Получение активностей, связанных с потребностью.
        
        Args:
            need_id: Идентификатор потребности
            
        Returns:
            Кортеж из списка связей потребности с активностями и флага существования потребности
        """
        # Проверяем существование потребности
        need_exists = await self._check_need_exists(need_id)
        
        if not need_exists:
            return [], False
        
        query = (
            select(ActivityNeed)
            .options(joinedload(ActivityNeed.activity))
            .where(ActivityNeed.need_id == need_id)
        )
        result = await self.db.execute(query)
        return result.scalars().all(), True
    
    async def link_activity_to_need(self, activity_id: UUID, need_id: UUID, 
                                    strength: float, expected_impact: float = None, 
                                    notes: str = None) -> ActivityNeed:
        """
        Создание или обновление связи между активностью и потребностью.
        
        Args:
            activity_id: Идентификатор активности
            need_id: Идентификатор потребности
            strength: Сила связи между активностью и потребностью (1-5)
            expected_impact: Ожидаемое влияние активности на потребность (1-5)
            notes: Заметки о связи
            
        Returns:
            Созданная или обновленная связь
            
        Raises:
            ValueError: Если strength или expected_impact вне диапазона 1-5
            ValueError: Если указанная активность или потребность не существует
        """
        # Проверяем диапазон значений
        if not (1 <= strength <= 5):
            raise ValueError("Значение силы связи должно быть в диапазоне от 1 до 5")
            
        if expected_impact is not None and not (1 <= expected_impact <= 5):
            raise ValueError("Значение ожидаемого влияния должно быть в диапазоне от 1 до 5")
            
        # Проверяем существование активности и потребности
        activity_exists = await self._check_activity_exists(activity_id)
        need_exists = await self._check_need_exists(need_id)
        
        if not activity_exists:
            raise ValueError(f"Активность с ID {activity_id} не существует")
        
        if not need_exists:
            raise ValueError(f"Потребность с ID {need_id} не существует")
        
        # Проверяем, существует ли уже такая связь
        query = select(ActivityNeed).where(
            ActivityNeed.activity_id == activity_id,
            ActivityNeed.need_id == need_id
        )
        result = await self.db.execute(query)
        existing_link = result.scalars().first()
        
        link_data = {
            "activity_id": activity_id,
            "need_id": need_id,
            "strength": strength
        }
        
        if expected_impact:
            link_data["expected_impact"] = expected_impact
        
        if notes:
            link_data["notes"] = notes
        
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
    
    async def update_link_strength(self, activity_id: UUID, need_id: UUID, 
                                  strength: float) -> Optional[ActivityNeed]:
        """
        Обновление силы связи между активностью и потребностью.
        
        Args:
            activity_id: Идентификатор активности
            need_id: Идентификатор потребности
            strength: Новое значение силы связи (1-5)
            
        Returns:
            Обновленная связь или None, если связь не найдена
            
        Raises:
            ValueError: Если strength вне диапазона 1-5
            ValueError: Если указанная активность или потребность не существует
        """
        # Проверяем диапазон значения
        if not (1 <= strength <= 5):
            raise ValueError("Значение силы связи должно быть в диапазоне от 1 до 5")
            
        # Проверяем существование активности и потребности
        activity_exists = await self._check_activity_exists(activity_id)
        need_exists = await self._check_need_exists(need_id)
        
        if not activity_exists:
            raise ValueError(f"Активность с ID {activity_id} не существует")
        
        if not need_exists:
            raise ValueError(f"Потребность с ID {need_id} не существует")
            
        return await self.update_link(activity_id, need_id, {"strength": strength})
    
    async def update_link(self, activity_id: UUID, need_id: UUID, 
                          update_data: Dict[str, Any]) -> Optional[ActivityNeed]:
        """
        Обновление параметров связи между активностью и потребностью.
        
        Args:
            activity_id: Идентификатор активности
            need_id: Идентификатор потребности
            update_data: Словарь с обновляемыми параметрами
            
        Returns:
            Обновленная связь или None, если связь не найдена
            
        Raises:
            ValueError: Если значения не соответствуют ограничениям
        """
        # Проверяем ограничения на значения параметров
        if "strength" in update_data and not (1 <= update_data["strength"] <= 5):
            raise ValueError("Значение силы связи должно быть в диапазоне от 1 до 5")
            
        if "expected_impact" in update_data and not (1 <= update_data["expected_impact"] <= 5):
            raise ValueError("Значение ожидаемого влияния должно быть в диапазоне от 1 до 5")
            
        if "actual_impact" in update_data and update_data["actual_impact"] is not None and not (1 <= update_data["actual_impact"] <= 5):
            raise ValueError("Значение фактического влияния должно быть в диапазоне от 1 до 5")
        
        # Проверяем существование связи
        query = select(ActivityNeed).where(
            ActivityNeed.activity_id == activity_id,
            ActivityNeed.need_id == need_id
        )
        result = await self.db.execute(query)
        existing_link = result.scalars().first()
        
        if not existing_link:
            return None
            
        # Обновляем связь
        for key, value in update_data.items():
            setattr(existing_link, key, value)
            
        await self.db.flush()
        await self.db.refresh(existing_link)
        
        return existing_link
    
    async def delete_link(self, activity_id: UUID, need_id: UUID) -> bool:
        """
        Удаление связи между активностью и потребностью.
        
        Args:
            activity_id: Идентификатор активности
            need_id: Идентификатор потребности
            
        Returns:
            True, если связь успешно удалена, иначе False
            
        Raises:
            ValueError: Если указанная активность или потребность не существует
        """
        # Проверяем существование активности и потребности
        activity_exists = await self._check_activity_exists(activity_id)
        need_exists = await self._check_need_exists(need_id)
        
        if not activity_exists:
            raise ValueError(f"Активность с ID {activity_id} не существует")
        
        if not need_exists:
            raise ValueError(f"Потребность с ID {need_id} не существует")
        
        # Проверяем существование связи
        query = select(ActivityNeed).where(
            ActivityNeed.activity_id == activity_id,
            ActivityNeed.need_id == need_id
        )
        result = await self.db.execute(query)
        existing_link = result.scalars().first()
        
        if not existing_link:
            return False
            
        # Удаляем связь
        await self.db.delete(existing_link)
        await self.db.flush()
        
        return True
    
    async def get_needs_with_strong_link(self, activity_id: UUID, threshold: int = 4) -> Tuple[List[ActivityNeed], bool]:
        """
        Получение потребностей с сильной связью с активностью.
        
        Args:
            activity_id: Идентификатор активности
            threshold: Пороговое значение силы связи (по умолчанию 4)
            
        Returns:
            Кортеж из списка связей с силой выше порогового значения и флага существования активности
            
        Raises:
            ValueError: Если threshold вне диапазона 1-5
        """
        # Проверяем диапазон значения
        if not (1 <= threshold <= 5):
            raise ValueError("Пороговое значение силы связи должно быть в диапазоне от 1 до 5")
            
        # Проверяем существование активности
        activity_exists = await self._check_activity_exists(activity_id)
        
        if not activity_exists:
            return [], False
            
        query = (
            select(ActivityNeed)
            .options(joinedload(ActivityNeed.need))
            .where(
                ActivityNeed.activity_id == activity_id,
                ActivityNeed.strength >= threshold
            )
        )
        result = await self.db.execute(query)
        return result.scalars().all(), True
    
    async def set_actual_impact(self, activity_id: UUID, need_id: UUID, 
                               actual_impact: int) -> Optional[ActivityNeed]:
        """
        Установка фактического влияния активности на потребность.
        
        Args:
            activity_id: Идентификатор активности
            need_id: Идентификатор потребности
            actual_impact: Фактическое влияние (1-5)
            
        Returns:
            Обновленная связь или None, если связь не найдена
            
        Raises:
            ValueError: Если actual_impact вне диапазона 1-5
            ValueError: Если указанная активность или потребность не существует
        """
        # Проверяем диапазон значения
        if not (1 <= actual_impact <= 5):
            raise ValueError("Значение фактического влияния должно быть в диапазоне от 1 до 5")
            
        # Проверяем существование активности и потребности
        activity_exists = await self._check_activity_exists(activity_id)
        need_exists = await self._check_need_exists(need_id)
        
        if not activity_exists:
            raise ValueError(f"Активность с ID {activity_id} не существует")
        
        if not need_exists:
            raise ValueError(f"Потребность с ID {need_id} не существует")
            
        return await self.update_link(activity_id, need_id, {"actual_impact": actual_impact})
    
    async def _check_activity_exists(self, activity_id: UUID) -> bool:
        """
        Проверяет существование активности.
        
        Args:
            activity_id: UUID активности
            
        Returns:
            True, если активность существует, иначе False
        """
        query = select(Activity).where(Activity.id == activity_id, Activity.is_active == True)
        result = await self.db.execute(query)
        return result.scalars().first() is not None
    
    async def _check_need_exists(self, need_id: UUID) -> bool:
        """
        Проверяет существование потребности.
        
        Args:
            need_id: UUID потребности
            
        Returns:
            True, если потребность существует, иначе False
        """
        query = select(Need).where(Need.id == need_id, Need.is_active == True)
        result = await self.db.execute(query)
        return result.scalars().first() is not None