"""
Репозиторий для работы с типами активностей.
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.repositories.base_repository import BaseRepository
from app.models.activity_types import ActivityType


class ActivityTypeRepository(BaseRepository):
    """
    Репозиторий для работы с типами активностей.
    Наследуется от BaseRepository и добавляет специфические методы для модели ActivityType.
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Инициализация репозитория.
        
        Args:
            db_session: Асинхронная сессия базы данных
        """
        super().__init__(db_session, ActivityType)
    
    async def get_all_types(self) -> List[ActivityType]:
        """
        Получение всех типов активностей.
        
        Returns:
            Список всех типов активностей
        """
        try:
            # Используем базовый метод list
            return await self.list(
                filters={"is_active": True},
                order_by=["name"]  # Сортировка по названию
            )
        except Exception as e:
            # Обработка ошибок
            raise e
    
    async def get_type_by_name(self, name: str) -> Optional[ActivityType]:
        """
        Получение типа активности по названию.
        
        Args:
            name: Название типа активности
            
        Returns:
            Тип активности или None, если не найден
        """
        try:
            query = select(ActivityType).where(
                ActivityType.name == name,
                ActivityType.is_active == True
            )
            result = await self.db.execute(query)
            return result.scalars().first()
        except Exception as e:
            # Обработка ошибок
            raise e
    
    async def create_type(self, type_data: Dict[str, Any]) -> ActivityType:
        """
        Создание нового типа активности.
        
        Args:
            type_data: Словарь с данными типа активности
            
        Returns:
            Созданный тип активности
            
        Raises:
            IntegrityError: Если тип с таким названием уже существует
            Exception: При ошибке создания
        """
        try:
            # Проверяем, существует ли тип с таким названием
            existing_type = await self.get_type_by_name(type_data["name"])
            if existing_type:
                # Если тип с таким названием уже существует
                raise IntegrityError(
                    "Тип активности с таким названием уже существует",
                    params={"name": type_data["name"]},
                    orig=None
                )
            
            # Создаем новый тип
            return await self.create(type_data)
        except IntegrityError as e:
            # Обработка ошибки уникальности
            raise e
        except Exception as e:
            # Обработка других ошибок
            raise e
    
    async def update_type(self, type_id: UUID, type_data: Dict[str, Any]) -> Optional[ActivityType]:
        """
        Обновление типа активности.
        
        Args:
            type_id: UUID типа активности
            type_data: Словарь с обновленными данными
            
        Returns:
            Обновленный тип активности или None, если тип не найден
            
        Raises:
            IntegrityError: Если тип с таким названием уже существует
            Exception: При ошибке обновления
        """
        try:
            # Если обновляется название, проверяем его уникальность
            if "name" in type_data:
                # Проверяем, существует ли другой тип с таким именем
                query = select(ActivityType).where(
                    ActivityType.name == type_data["name"],
                    ActivityType.id != type_id,
                    ActivityType.is_active == True
                )
                result = await self.db.execute(query)
                existing_type = result.scalars().first()
                
                if existing_type:
                    # Если тип с таким названием уже существует
                    raise IntegrityError(
                        "Тип активности с таким названием уже существует",
                        params={"name": type_data["name"]},
                        orig=None
                    )
            
            # Обновляем тип
            return await self.update(type_id, type_data)
        except IntegrityError as e:
            # Обработка ошибки уникальности
            raise e
        except Exception as e:
            # Обработка других ошибок
            raise e
    
    async def delete_type(self, type_id: UUID, check_dependencies: bool = True) -> bool:
        """
        Мягкое удаление типа активности.
        
        Args:
            type_id: UUID типа активности
            check_dependencies: Если True, проверяет наличие связанных активностей
            
        Returns:
            True, если тип успешно удален, иначе False
            
        Raises:
            ValueError: Если type_id связан с активностями и check_dependencies=True
            Exception: При ошибке удаления
        """
        try:
            # Проверяем наличие связанных активностей
            if check_dependencies:
                activity_type = await self.get_by_id(type_id)
                if activity_type and activity_type.activities:
                    # Получаем количество связанных активностей
                    query = select(func.count()).select_from(ActivityType).join(
                        ActivityType.activities
                    ).where(ActivityType.id == type_id)
                    result = await self.db.execute(query)
                    count = result.scalar()
                    
                    if count > 0:
                        raise ValueError(
                            f"Невозможно удалить тип активности, так как с ним связано {count} активностей"
                        )
            
            # Мягкое удаление
            return await self.delete(type_id, soft_delete=True)
        except ValueError as e:
            # Обработка ошибки зависимостей
            raise e
        except Exception as e:
            # Обработка других ошибок
            raise e