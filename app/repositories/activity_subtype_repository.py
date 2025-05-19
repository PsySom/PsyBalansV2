"""
Репозиторий для работы с подтипами активностей.
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.repositories.base_repository import BaseRepository
from app.models.activity_types import ActivitySubtype, ActivityType


class ActivitySubtypeRepository(BaseRepository):
    """
    Репозиторий для работы с подтипами активностей.
    Наследуется от BaseRepository и добавляет специфические методы для модели ActivitySubtype.
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Инициализация репозитория.
        
        Args:
            db_session: Асинхронная сессия базы данных
        """
        super().__init__(db_session, ActivitySubtype)
    
    async def get_subtypes_by_type(self, type_id: UUID) -> List[ActivitySubtype]:
        """
        Получение подтипов для указанного типа активности.
        
        Args:
            type_id: UUID типа активности
            
        Returns:
            Список подтипов для указанного типа
        """
        try:
            # Получаем подтипы для указанного типа
            return await self.list(
                filters={"activity_type_id": type_id, "is_active": True},
                order_by=["name"]  # Сортировка по названию
            )
        except Exception as e:
            # Обработка ошибок
            raise e
    
    async def get_subtype_by_id(self, subtype_id: UUID, with_type: bool = False) -> Optional[ActivitySubtype]:
        """
        Получение подтипа по ID.
        
        Args:
            subtype_id: UUID подтипа активности
            with_type: Если True, загружает связанный тип активности
            
        Returns:
            Подтип активности или None, если не найден
        """
        try:
            if with_type:
                # Получаем подтип с загрузкой типа
                query = (
                    select(ActivitySubtype)
                    .options(joinedload(ActivitySubtype.activity_type))
                    .where(
                        ActivitySubtype.id == subtype_id,
                        ActivitySubtype.is_active == True
                    )
                )
                result = await self.db.execute(query)
                return result.scalars().first()
            else:
                # Используем базовый метод get_by_id
                subtype = await self.get_by_id(subtype_id)
                if subtype and not subtype.is_active:
                    return None
                return subtype
        except Exception as e:
            # Обработка ошибок
            raise e
    
    async def get_subtype_by_name_and_type(self, name: str, type_id: UUID) -> Optional[ActivitySubtype]:
        """
        Получение подтипа по названию и типу активности.
        
        Args:
            name: Название подтипа
            type_id: UUID типа активности
            
        Returns:
            Подтип активности или None, если не найден
        """
        try:
            query = select(ActivitySubtype).where(
                ActivitySubtype.name == name,
                ActivitySubtype.activity_type_id == type_id,
                ActivitySubtype.is_active == True
            )
            result = await self.db.execute(query)
            return result.scalars().first()
        except Exception as e:
            # Обработка ошибок
            raise e
    
    async def create_subtype(self, subtype_data: Dict[str, Any]) -> ActivitySubtype:
        """
        Создание нового подтипа активности.
        
        Args:
            subtype_data: Словарь с данными подтипа активности
            
        Returns:
            Созданный подтип активности
            
        Raises:
            IntegrityError: Если подтип с таким названием уже существует для указанного типа
            ValueError: Если указанный тип активности не существует
            Exception: При ошибке создания
        """
        try:
            # Проверяем существование типа активности
            if "activity_type_id" in subtype_data:
                type_id = subtype_data["activity_type_id"]
                
                # Проверяем, существует ли указанный тип
                query = select(ActivityType).where(
                    ActivityType.id == type_id,
                    ActivityType.is_active == True
                )
                result = await self.db.execute(query)
                activity_type = result.scalars().first()
                
                if not activity_type:
                    raise ValueError(f"Тип активности с ID {type_id} не существует")
                
                # Проверяем, существует ли подтип с таким именем для указанного типа
                if "name" in subtype_data:
                    existing_subtype = await self.get_subtype_by_name_and_type(
                        subtype_data["name"], type_id
                    )
                    
                    if existing_subtype:
                        raise IntegrityError(
                            "Подтип активности с таким названием уже существует для указанного типа",
                            params={"name": subtype_data["name"], "type_id": type_id},
                            orig=None
                        )
            
            # Создаем новый подтип
            return await self.create(subtype_data)
        except IntegrityError as e:
            # Обработка ошибки уникальности
            raise e
        except ValueError as e:
            # Обработка ошибки отсутствия типа
            raise e
        except Exception as e:
            # Обработка других ошибок
            raise e
    
    async def update_subtype(self, subtype_id: UUID, subtype_data: Dict[str, Any]) -> Optional[ActivitySubtype]:
        """
        Обновление подтипа активности.
        
        Args:
            subtype_id: UUID подтипа активности
            subtype_data: Словарь с обновленными данными
            
        Returns:
            Обновленный подтип активности или None, если подтип не найден
            
        Raises:
            IntegrityError: Если подтип с таким названием уже существует для указанного типа
            ValueError: Если указанный тип активности не существует
            Exception: При ошибке обновления
        """
        try:
            # Получаем текущий подтип
            current_subtype = await self.get_by_id(subtype_id)
            if not current_subtype:
                return None
            
            # Проверяем, меняется ли тип активности
            type_id = subtype_data.get("activity_type_id", current_subtype.activity_type_id)
            
            # Проверяем существование типа активности, если он меняется
            if "activity_type_id" in subtype_data:
                # Проверяем, существует ли указанный тип
                query = select(ActivityType).where(
                    ActivityType.id == type_id,
                    ActivityType.is_active == True
                )
                result = await self.db.execute(query)
                activity_type = result.scalars().first()
                
                if not activity_type:
                    raise ValueError(f"Тип активности с ID {type_id} не существует")
            
            # Проверяем уникальность имени в рамках типа, если имя меняется
            if "name" in subtype_data:
                new_name = subtype_data["name"]
                
                # Проверяем, существует ли другой подтип с таким именем для указанного типа
                query = select(ActivitySubtype).where(
                    ActivitySubtype.name == new_name,
                    ActivitySubtype.activity_type_id == type_id,
                    ActivitySubtype.id != subtype_id,
                    ActivitySubtype.is_active == True
                )
                result = await self.db.execute(query)
                existing_subtype = result.scalars().first()
                
                if existing_subtype:
                    raise IntegrityError(
                        "Подтип активности с таким названием уже существует для указанного типа",
                        params={"name": new_name, "type_id": type_id},
                        orig=None
                    )
            
            # Обновляем подтип
            return await self.update(subtype_id, subtype_data)
        except IntegrityError as e:
            # Обработка ошибки уникальности
            raise e
        except ValueError as e:
            # Обработка ошибки отсутствия типа
            raise e
        except Exception as e:
            # Обработка других ошибок
            raise e
    
    async def delete_subtype(self, subtype_id: UUID, check_dependencies: bool = True) -> bool:
        """
        Мягкое удаление подтипа активности.
        
        Args:
            subtype_id: UUID подтипа активности
            check_dependencies: Если True, проверяет наличие связанных активностей
            
        Returns:
            True, если подтип успешно удален, иначе False
            
        Raises:
            ValueError: Если subtype_id связан с активностями и check_dependencies=True
            Exception: При ошибке удаления
        """
        try:
            # Проверяем наличие связанных активностей
            if check_dependencies:
                subtype = await self.get_by_id(subtype_id)
                if subtype and subtype.activities:
                    # Получаем количество связанных активностей
                    query = select(func.count()).select_from(ActivitySubtype).join(
                        ActivitySubtype.activities
                    ).where(ActivitySubtype.id == subtype_id)
                    result = await self.db.execute(query)
                    count = result.scalar()
                    
                    if count > 0:
                        raise ValueError(
                            f"Невозможно удалить подтип активности, так как с ним связано {count} активностей"
                        )
            
            # Мягкое удаление
            return await self.delete(subtype_id, soft_delete=True)
        except ValueError as e:
            # Обработка ошибки зависимостей
            raise e
        except Exception as e:
            # Обработка других ошибок
            raise e