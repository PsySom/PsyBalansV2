"""
Репозиторий для работы с потребностями пользователей.
"""
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.repositories.base_repository import BaseRepository
from app.models.needs import Need, NeedCategory


class NeedRepository(BaseRepository):
    """
    Репозиторий для работы с потребностями пользователей.
    Наследуется от BaseRepository и добавляет специфические методы для модели Need.
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Инициализация репозитория.
        
        Args:
            db_session: Асинхронная сессия базы данных
        """
        super().__init__(db_session, Need)
    
    async def get_need_by_id(self, need_id: UUID) -> Optional[Need]:
        """
        Получение потребности по ID.
        
        Args:
            need_id: UUID потребности
            
        Returns:
            Объект потребности или None, если потребность не найдена
        """
        try:
            # Используем базовый метод get_by_id
            need = await self.get_by_id(need_id)
            if need and not need.is_active:
                return None
            return need
        except Exception as e:
            # Обработка ошибок
            raise e
    
    async def get_need_by_id_with_category(self, need_id: UUID) -> Optional[Need]:
        """
        Получение потребности по ID с загрузкой категории.
        
        Args:
            need_id: UUID потребности
            
        Returns:
            Объект потребности с загруженной категорией или None, если потребность не найдена
        """
        try:
            query = (
                select(Need)
                .options(joinedload(Need.category))
                .where(
                    Need.id == need_id,
                    Need.is_active == True
                )
            )
            result = await self.db.execute(query)
            return result.scalars().first()
        except Exception as e:
            # Обработка ошибок
            raise e
    
    async def get_all_needs(
        self, 
        user_id: Optional[UUID] = None,
        include_inactive: bool = False,
        include_custom: bool = True,
        pagination: Optional[Dict[str, int]] = None,
        order_by: Optional[List[str]] = None
    ) -> Tuple[List[Need], int]:
        """
        Получение всех потребностей с возможностью фильтрации и пагинации.
        
        Args:
            user_id: UUID пользователя для фильтрации (опционально)
            include_inactive: Если True, включает неактивные потребности
            include_custom: Если True, включает пользовательские потребности
            pagination: Словарь с параметрами пагинации {'skip': int, 'limit': int}
            order_by: Список полей для сортировки ["field_name", "-field_name"]
            
        Returns:
            Кортеж (список потребностей, общее количество)
        """
        try:
            filters = {}
            
            # Фильтр по пользователю
            if user_id:
                filters["user_id"] = user_id
            
            # Фильтр по активности
            if not include_inactive:
                filters["is_active"] = True
            
            # Фильтр по типу потребности (стандартная или пользовательская)
            if not include_custom:
                filters["is_custom"] = False
            
            # Сортировка по умолчанию
            if not order_by:
                order_by = ["category_id", "name"]  # Сначала по категории, затем по имени
            
            # Получаем общее количество
            total_count = await self.count(filters)
            
            # Получаем список с пагинацией
            needs = await self.list(filters, pagination, order_by)
            
            return needs, total_count
        except Exception as e:
            # Обработка ошибок
            raise e
    
    async def get_needs_by_category(
        self, 
        category_id: UUID,
        user_id: Optional[UUID] = None,
        include_inactive: bool = False,
        pagination: Optional[Dict[str, int]] = None
    ) -> Tuple[List[Need], int]:
        """
        Получение потребностей по категории.
        
        Args:
            category_id: UUID категории потребностей
            user_id: UUID пользователя для фильтрации (опционально)
            include_inactive: Если True, включает неактивные потребности
            pagination: Словарь с параметрами пагинации {'skip': int, 'limit': int}
            
        Returns:
            Кортеж (список потребностей, общее количество)
        """
        try:
            filters = {"category_id": category_id}
            
            # Фильтр по пользователю
            if user_id:
                filters["user_id"] = user_id
            
            # Фильтр по активности
            if not include_inactive:
                filters["is_active"] = True
            
            # Получаем общее количество
            total_count = await self.count(filters)
            
            # Получаем список с пагинацией
            needs = await self.list(filters, pagination, ["name"])  # Сортировка по имени
            
            return needs, total_count
        except Exception as e:
            # Обработка ошибок
            raise e
    
    async def get_need_by_name_and_user(self, name: str, user_id: UUID) -> Optional[Need]:
        """
        Получение потребности по названию и пользователю.
        
        Args:
            name: Название потребности
            user_id: UUID пользователя
            
        Returns:
            Объект потребности или None, если потребность не найдена
        """
        try:
            query = select(Need).where(
                Need.name == name,
                Need.user_id == user_id,
                Need.is_active == True
            )
            result = await self.db.execute(query)
            return result.scalars().first()
        except Exception as e:
            # Обработка ошибок
            raise e
    
    async def create_need(self, need_data: Dict[str, Any]) -> Need:
        """
        Создание новой потребности.
        
        Args:
            need_data: Словарь с данными потребности
            
        Returns:
            Созданный объект потребности
            
        Raises:
            IntegrityError: Если потребность с таким названием уже существует для данного пользователя
            ValueError: Если указанная категория не существует
            Exception: При ошибке создания
        """
        try:
            # Проверяем, существует ли потребность с таким названием для данного пользователя
            if "name" in need_data and "user_id" in need_data:
                existing_need = await self.get_need_by_name_and_user(
                    need_data["name"], need_data["user_id"]
                )
                
                if existing_need:
                    raise IntegrityError(
                        "Потребность с таким названием уже существует для данного пользователя",
                        params={"name": need_data["name"], "user_id": need_data["user_id"]},
                        orig=None
                    )
                    
            # Проверяем существование категории
            if "category_id" in need_data:
                category_id = need_data["category_id"]
                query = select(NeedCategory).where(
                    NeedCategory.id == category_id,
                    NeedCategory.is_active == True
                )
                result = await self.db.execute(query)
                category = result.scalars().first()
                
                if not category:
                    raise ValueError(f"Категория потребностей с ID {category_id} не существует")
            
            # Создаем новую потребность
            return await self.create(need_data)
        except IntegrityError as e:
            # Обработка ошибки уникальности
            raise e
        except ValueError as e:
            # Обработка ошибки отсутствия категории
            raise e
        except Exception as e:
            # Обработка других ошибок
            raise e
    
    async def update_need(self, need_id: UUID, need_data: Dict[str, Any]) -> Optional[Need]:
        """
        Обновление потребности.
        
        Args:
            need_id: UUID потребности
            need_data: Словарь с обновленными данными
            
        Returns:
            Обновленный объект потребности или None, если потребность не найдена
            
        Raises:
            IntegrityError: Если потребность с таким названием уже существует для данного пользователя
            ValueError: Если указанная категория не существует
            Exception: При ошибке обновления
        """
        try:
            # Получаем текущую потребность
            current_need = await self.get_by_id(need_id)
            if not current_need:
                return None
            
            # Проверяем уникальность имени, если имя меняется
            if "name" in need_data:
                user_id = need_data.get("user_id", current_need.user_id)
                
                # Проверяем, существует ли другая потребность с таким именем для данного пользователя
                query = select(Need).where(
                    Need.name == need_data["name"],
                    Need.user_id == user_id,
                    Need.id != need_id,
                    Need.is_active == True
                )
                result = await self.db.execute(query)
                existing_need = result.scalars().first()
                
                if existing_need:
                    raise IntegrityError(
                        "Потребность с таким названием уже существует для данного пользователя",
                        params={"name": need_data["name"], "user_id": user_id},
                        orig=None
                    )
            
            # Проверяем существование категории, если она меняется
            if "category_id" in need_data:
                category_id = need_data["category_id"]
                query = select(NeedCategory).where(
                    NeedCategory.id == category_id,
                    NeedCategory.is_active == True
                )
                result = await self.db.execute(query)
                category = result.scalars().first()
                
                if not category:
                    raise ValueError(f"Категория потребностей с ID {category_id} не существует")
            
            # Обновляем потребность
            return await self.update(need_id, need_data)
        except IntegrityError as e:
            # Обработка ошибки уникальности
            raise e
        except ValueError as e:
            # Обработка ошибки отсутствия категории
            raise e
        except Exception as e:
            # Обработка других ошибок
            raise e
    
    async def delete_need(self, need_id: UUID, check_dependencies: bool = True) -> bool:
        """
        Мягкое удаление потребности.
        
        Args:
            need_id: UUID потребности
            check_dependencies: Если True, проверяет наличие связанных активностей
            
        Returns:
            True, если потребность успешно удалена, иначе False
            
        Raises:
            ValueError: Если need_id связан с активностями и check_dependencies=True
            Exception: При ошибке удаления
        """
        try:
            # Проверяем наличие связанных активностей
            if check_dependencies:
                need = await self.get_by_id(need_id)
                if need and need.activity_needs:
                    # Получаем количество связанных активностей
                    query = select(func.count()).select_from(Need).join(
                        Need.activity_needs
                    ).where(Need.id == need_id)
                    result = await self.db.execute(query)
                    count = result.scalar()
                    
                    if count > 0:
                        raise ValueError(
                            f"Невозможно удалить потребность, так как с ней связано {count} активностей"
                        )
            
            # Мягкое удаление
            return await self.delete(need_id, soft_delete=True)
        except ValueError as e:
            # Обработка ошибки зависимостей
            raise e
        except Exception as e:
            # Обработка других ошибок
            raise e