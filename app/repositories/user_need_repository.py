"""
Репозиторий для работы с потребностями пользователя.
"""
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.repositories.base_repository import BaseRepository
from app.models.user_needs import UserNeed, UserNeedHistory
from app.models.needs import Need
from app.models.user import User


class UserNeedRepository(BaseRepository):
    """
    Репозиторий для работы с потребностями пользователя.
    Наследуется от BaseRepository и добавляет специфические методы для модели UserNeed.
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Инициализация репозитория.
        
        Args:
            db_session: Асинхронная сессия базы данных
        """
        super().__init__(db_session, UserNeed)
    
    async def get_user_needs(
        self, 
        user_id: UUID, 
        include_inactive: bool = False,
        with_relations: bool = False,
        pagination: Optional[Dict[str, int]] = None,
        order_by: Optional[List[str]] = None
    ) -> Tuple[List[UserNeed], int]:
        """
        Получение всех потребностей пользователя.
        
        Args:
            user_id: UUID пользователя
            include_inactive: Если True, включает неактивные записи
            with_relations: Если True, загружает связанные сущности (need, need.category)
            pagination: Словарь с параметрами пагинации {'skip': int, 'limit': int}
            order_by: Список полей для сортировки ["field_name", "-field_name"]
            
        Returns:
            Кортеж (список потребностей пользователя, общее количество)
            
        Raises:
            ValueError: Если пользователь не существует
            Exception: При ошибке получения данных
        """
        try:
            # Проверяем существование пользователя
            user_exists = await self._check_user_exists(user_id)
            if not user_exists:
                raise ValueError(f"Пользователь с ID {user_id} не существует")
            
            # Формируем фильтры
            filters = {"user_id": user_id}
            if not include_inactive:
                filters["is_active"] = True
            
            # Сортировка по умолчанию
            if not order_by:
                # Сортировка по важности (от наиболее важных)
                order_by = ["-importance", "need_id"]
            
            # Получаем общее количество
            total_count = await self.count(filters)
            
            if with_relations:
                # Используем собственный запрос для загрузки связанных сущностей
                query = (
                    select(UserNeed)
                    .options(
                        joinedload(UserNeed.need).joinedload(Need.category)
                    )
                    .where(UserNeed.user_id == user_id)
                )
                
                if not include_inactive:
                    query = query.where(UserNeed.is_active == True)
                
                # Применяем сортировку
                for field_name in order_by:
                    if field_name.startswith("-"):
                        # Сортировка по убыванию
                        field_name = field_name[1:]
                        if hasattr(UserNeed, field_name):
                            query = query.order_by(getattr(UserNeed, field_name).desc())
                    else:
                        # Сортировка по возрастанию
                        if hasattr(UserNeed, field_name):
                            query = query.order_by(getattr(UserNeed, field_name).asc())
                
                # Применяем пагинацию
                if pagination:
                    skip = pagination.get("skip", 0)
                    limit = pagination.get("limit", 100)
                    query = query.offset(skip).limit(limit)
                
                result = await self.db.execute(query)
                user_needs = result.scalars().all()
            else:
                # Используем базовый метод list
                user_needs = await self.list(filters, pagination, order_by)
            
            return user_needs, total_count
        except ValueError as e:
            # Переадресуем ошибку валидации
            raise e
        except Exception as e:
            # Обработка других ошибок
            raise e
    
    async def get_user_need(
        self, 
        user_id: UUID, 
        need_id: UUID,
        with_relations: bool = False
    ) -> Optional[UserNeed]:
        """
        Получение конкретной потребности пользователя.
        
        Args:
            user_id: UUID пользователя
            need_id: UUID потребности
            with_relations: Если True, загружает связанные сущности (need, need.category)
            
        Returns:
            Объект UserNeed или None, если запись не найдена
            
        Raises:
            ValueError: Если пользователь не существует
            Exception: При ошибке получения данных
        """
        try:
            # Проверяем существование пользователя
            user_exists = await self._check_user_exists(user_id)
            if not user_exists:
                raise ValueError(f"Пользователь с ID {user_id} не существует")
            
            # Проверяем существование потребности
            need_exists = await self._check_need_exists(need_id)
            if not need_exists:
                raise ValueError(f"Потребность с ID {need_id} не существует")
            
            if with_relations:
                # Используем собственный запрос для загрузки связанных сущностей
                query = (
                    select(UserNeed)
                    .options(
                        joinedload(UserNeed.need).joinedload(Need.category)
                    )
                    .where(
                        UserNeed.user_id == user_id,
                        UserNeed.need_id == need_id,
                        UserNeed.is_active == True
                    )
                )
                result = await self.db.execute(query)
                return result.scalars().first()
            else:
                # Используем фильтр для получения объекта
                query = select(UserNeed).where(
                    UserNeed.user_id == user_id,
                    UserNeed.need_id == need_id,
                    UserNeed.is_active == True
                )
                result = await self.db.execute(query)
                return result.scalars().first()
        except ValueError as e:
            # Переадресуем ошибку валидации
            raise e
        except Exception as e:
            # Обработка других ошибок
            raise e
    
    async def get_user_need_by_id(
        self, 
        user_need_id: UUID,
        with_relations: bool = False
    ) -> Optional[UserNeed]:
        """
        Получение потребности пользователя по ID связи.
        
        Args:
            user_need_id: UUID связи UserNeed
            with_relations: Если True, загружает связанные сущности (need, need.category)
            
        Returns:
            Объект UserNeed или None, если запись не найдена
        """
        try:
            if with_relations:
                # Используем собственный запрос для загрузки связанных сущностей
                query = (
                    select(UserNeed)
                    .options(
                        joinedload(UserNeed.need).joinedload(Need.category)
                    )
                    .where(
                        UserNeed.id == user_need_id,
                        UserNeed.is_active == True
                    )
                )
                result = await self.db.execute(query)
                return result.scalars().first()
            else:
                # Используем базовый метод get_by_id
                user_need = await self.get_by_id(user_need_id)
                if user_need and not user_need.is_active:
                    return None
                return user_need
        except Exception as e:
            # Обработка ошибок
            raise e
    
    async def update_satisfaction_level(
        self, 
        user_id: UUID, 
        need_id: UUID, 
        level: float,
        note: Optional[str] = None,
        context: Optional[str] = None
    ) -> Optional[Tuple[UserNeed, UserNeedHistory]]:
        """
        Обновление уровня удовлетворенности потребности.
        
        Args:
            user_id: UUID пользователя
            need_id: UUID потребности
            level: Новый уровень удовлетворенности (-5.0 до 5.0)
            note: Опциональное примечание к изменению
            context: Опциональный контекст изменения (например, 'morning_check', 'activity_completion')
            
        Returns:
            Кортеж (обновленный объект UserNeed, запись истории) или None, если запись не найдена
            
        Raises:
            ValueError: Если пользователь или потребность не существуют, или уровень вне диапазона
            Exception: При ошибке обновления
        """
        try:
            # Проверяем существование пользователя
            user_exists = await self._check_user_exists(user_id)
            if not user_exists:
                raise ValueError(f"Пользователь с ID {user_id} не существует")
            
            # Проверяем существование потребности
            need_exists = await self._check_need_exists(need_id)
            if not need_exists:
                raise ValueError(f"Потребность с ID {need_id} не существует")
            
            # Проверяем диапазон значения уровня удовлетворенности
            if not (-5.0 <= level <= 5.0):
                raise ValueError("Уровень удовлетворенности должен быть в диапазоне от -5.0 до 5.0")
            
            # Получаем текущую связь
            user_need = await self.get_user_need(user_id, need_id)
            if not user_need:
                return None
            
            # Сохраняем старое значение для записи в историю
            old_value = user_need.current_satisfaction
            
            # Обновляем уровень удовлетворенности
            user_need.current_satisfaction = level
            
            # Создаем запись в истории
            history_entry = UserNeedHistory(
                user_need_id=user_need.id,
                user_id=user_id,
                need_id=need_id,
                satisfaction_level=level,
                previous_value=old_value,
                change_value=level - old_value,
                note=note,
                context=context
            )
            
            # Сохраняем запись в истории
            self.db.add(history_entry)
            
            # Сохраняем изменения
            await self.db.flush()
            await self.db.refresh(user_need)
            await self.db.refresh(history_entry)
            
            return user_need, history_entry
        except ValueError as e:
            # Переадресуем ошибку валидации
            raise e
        except Exception as e:
            # Обработка других ошибок
            raise e
    
    async def get_needs_below_threshold(
        self, 
        user_id: UUID, 
        threshold: float,
        with_relations: bool = False,
        pagination: Optional[Dict[str, int]] = None
    ) -> Tuple[List[UserNeed], int]:
        """
        Получение потребностей с уровнем удовлетворенности ниже порога.
        
        Args:
            user_id: UUID пользователя
            threshold: Пороговое значение уровня удовлетворенности
            with_relations: Если True, загружает связанные сущности (need, need.category)
            pagination: Словарь с параметрами пагинации {'skip': int, 'limit': int}
            
        Returns:
            Кортеж (список потребностей ниже порога, общее количество)
            
        Raises:
            ValueError: Если пользователь не существует
            Exception: При ошибке получения данных
        """
        try:
            # Проверяем существование пользователя
            user_exists = await self._check_user_exists(user_id)
            if not user_exists:
                raise ValueError(f"Пользователь с ID {user_id} не существует")
            
            # Базовый запрос
            base_query = (
                select(UserNeed)
                .where(
                    UserNeed.user_id == user_id,
                    UserNeed.current_satisfaction < threshold,
                    UserNeed.is_active == True
                )
            )
            
            # Загружаем связанные сущности, если требуется
            if with_relations:
                base_query = base_query.options(
                    joinedload(UserNeed.need).joinedload(Need.category)
                )
            
            # Сортируем по уровню удовлетворенности (от самого низкого)
            base_query = base_query.order_by(UserNeed.current_satisfaction.asc())
            
            # Считаем общее количество
            count_query = select(func.count()).select_from(UserNeed).where(
                UserNeed.user_id == user_id,
                UserNeed.current_satisfaction < threshold,
                UserNeed.is_active == True
            )
            count_result = await self.db.execute(count_query)
            total_count = count_result.scalar()
            
            # Применяем пагинацию
            if pagination:
                skip = pagination.get("skip", 0)
                limit = pagination.get("limit", 100)
                base_query = base_query.offset(skip).limit(limit)
            
            # Выполняем запрос
            result = await self.db.execute(base_query)
            user_needs = result.scalars().all()
            
            return user_needs, total_count
        except ValueError as e:
            # Переадресуем ошибку валидации
            raise e
        except Exception as e:
            # Обработка других ошибок
            raise e
    
    async def create_user_need(self, user_need_data: Dict[str, Any]) -> UserNeed:
        """
        Создание связи между пользователем и потребностью.
        
        Args:
            user_need_data: Словарь с данными связи
            
        Returns:
            Созданный объект UserNeed
            
        Raises:
            ValueError: Если пользователь или потребность не существуют
            IntegrityError: Если связь уже существует
            Exception: При ошибке создания
        """
        try:
            # Проверяем обязательные поля
            if "user_id" not in user_need_data:
                raise ValueError("Отсутствует обязательное поле user_id")
            if "need_id" not in user_need_data:
                raise ValueError("Отсутствует обязательное поле need_id")
            
            user_id = user_need_data["user_id"]
            need_id = user_need_data["need_id"]
            
            # Проверяем существование пользователя
            user_exists = await self._check_user_exists(user_id)
            if not user_exists:
                raise ValueError(f"Пользователь с ID {user_id} не существует")
            
            # Проверяем существование потребности
            need_exists = await self._check_need_exists(need_id)
            if not need_exists:
                raise ValueError(f"Потребность с ID {need_id} не существует")
            
            # Проверяем, существует ли уже связь (включая мягко удаленные)
            existing_link = await self.get_user_need(user_id, need_id, with_relations=False)
            if existing_link:
                # Если связь существует, но мягко удалена, восстанавливаем её
                if not existing_link.is_active:
                    existing_link.is_active = True
                    
                    # Обновляем другие поля, если они переданы
                    for key, value in user_need_data.items():
                        if key not in ["user_id", "need_id"] and hasattr(existing_link, key):
                            setattr(existing_link, key, value)
                    
                    await self.db.flush()
                    await self.db.refresh(existing_link)
                    return existing_link
                else:
                    # Связь уже существует и активна
                    raise IntegrityError(
                        "Связь между пользователем и потребностью уже существует",
                        params={"user_id": user_id, "need_id": need_id},
                        orig=None
                    )
            
            # Создаем новую связь
            return await self.create(user_need_data)
        except ValueError as e:
            # Переадресуем ошибку валидации
            raise e
        except IntegrityError as e:
            # Переадресуем ошибку уникальности
            raise e
        except Exception as e:
            # Обработка других ошибок
            raise e
    
    async def update_user_need(
        self, 
        user_id: UUID, 
        need_id: UUID, 
        update_data: Dict[str, Any]
    ) -> Optional[UserNeed]:
        """
        Обновление связи между пользователем и потребностью.
        
        Args:
            user_id: UUID пользователя
            need_id: UUID потребности
            update_data: Словарь с обновляемыми данными
            
        Returns:
            Обновленный объект UserNeed или None, если связь не найдена
            
        Raises:
            ValueError: Если пользователь или потребность не существуют
            Exception: При ошибке обновления
        """
        try:
            # Проверяем существование пользователя
            user_exists = await self._check_user_exists(user_id)
            if not user_exists:
                raise ValueError(f"Пользователь с ID {user_id} не существует")
            
            # Проверяем существование потребности
            need_exists = await self._check_need_exists(need_id)
            if not need_exists:
                raise ValueError(f"Потребность с ID {need_id} не существует")
            
            # Получаем текущую связь
            user_need = await self.get_user_need(user_id, need_id)
            if not user_need:
                return None
            
            # Запрещаем изменение первичных ключей
            if "user_id" in update_data or "need_id" in update_data:
                raise ValueError("Невозможно изменить user_id или need_id")
            
            # Обновляем связь
            for key, value in update_data.items():
                if hasattr(user_need, key):
                    setattr(user_need, key, value)
            
            # Сохраняем изменения
            await self.db.flush()
            await self.db.refresh(user_need)
            
            return user_need
        except ValueError as e:
            # Переадресуем ошибку валидации
            raise e
        except Exception as e:
            # Обработка других ошибок
            raise e
    
    async def delete_user_need(
        self, 
        user_id: UUID, 
        need_id: UUID, 
        hard_delete: bool = False
    ) -> bool:
        """
        Удаление связи между пользователем и потребностью.
        
        Args:
            user_id: UUID пользователя
            need_id: UUID потребности
            hard_delete: Если True, выполняет физическое удаление, иначе мягкое
            
        Returns:
            True, если связь успешно удалена, иначе False
            
        Raises:
            ValueError: Если пользователь или потребность не существуют
            Exception: При ошибке удаления
        """
        try:
            # Проверяем существование пользователя
            user_exists = await self._check_user_exists(user_id)
            if not user_exists:
                raise ValueError(f"Пользователь с ID {user_id} не существует")
            
            # Проверяем существование потребности
            need_exists = await self._check_need_exists(need_id)
            if not need_exists:
                raise ValueError(f"Потребность с ID {need_id} не существует")
            
            # Получаем текущую связь
            user_need = await self.get_user_need(user_id, need_id)
            if not user_need:
                return False
            
            if hard_delete:
                # Физическое удаление
                await self.db.delete(user_need)
                await self.db.flush()
                return True
            else:
                # Мягкое удаление
                user_need.is_active = False
                await self.db.flush()
                return True
        except ValueError as e:
            # Переадресуем ошибку валидации
            raise e
        except Exception as e:
            # Обработка других ошибок
            raise e
    
    async def _check_user_exists(self, user_id: UUID) -> bool:
        """
        Проверяет существование пользователя.
        
        Args:
            user_id: UUID пользователя
            
        Returns:
            True, если пользователь существует, иначе False
        """
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalars().first()
        return user is not None
    
    async def _check_need_exists(self, need_id: UUID) -> bool:
        """
        Проверяет существование потребности.
        
        Args:
            need_id: UUID потребности
            
        Returns:
            True, если потребность существует, иначе False
        """
        query = select(Need).where(Need.id == need_id)
        result = await self.db.execute(query)
        need = result.scalars().first()
        return need is not None