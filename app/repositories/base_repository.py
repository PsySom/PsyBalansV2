"""
Базовый репозиторий, предоставляющий CRUD-операции для работы с моделями SQLAlchemy.
"""
from typing import TypeVar, Generic, Type, List, Optional, Dict, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.sql import Select
from uuid import UUID

from app.models.base import BaseModel
from app.core.database.postgresql import get_db

# Определение типа модели
T = TypeVar('T', bound=BaseModel)

class BaseRepository(Generic[T]):
    """
    Базовый репозиторий, предоставляющий CRUD-операции для моделей SQLAlchemy.
    """
    
    def __init__(self, db_session: AsyncSession, model_class: Type[T]):
        """
        Инициализация репозитория с сессией базы данных и классом модели.
        
        Args:
            db_session: Асинхронная сессия SQLAlchemy
            model_class: Класс модели SQLAlchemy для этого репозитория
        """
        self.db = db_session
        self.model = model_class
    
    async def create(self, model_data: Dict[str, Any]) -> T:
        """
        Создание новой записи в базе данных.
        
        Args:
            model_data: Словарь с данными для создания объекта
            
        Returns:
            Созданная модель
        """
        model_instance = self.model(**model_data)
        self.db.add(model_instance)
        await self.db.flush()
        await self.db.refresh(model_instance)
        return model_instance
    
    async def get_by_id(self, model_id: UUID) -> Optional[T]:
        """
        Получение записи по идентификатору.
        
        Args:
            model_id: Идентификатор модели
            
        Returns:
            Найденная модель или None
        """
        query = select(self.model).where(self.model.id == model_id)
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def update(self, model_id: UUID, model_data: Dict[str, Any]) -> Optional[T]:
        """
        Обновление существующей записи.
        
        Args:
            model_id: Идентификатор модели
            model_data: Словарь с обновленными данными
            
        Returns:
            Обновленная модель или None, если запись не найдена
        """
        model_instance = await self.get_by_id(model_id)
        if not model_instance:
            return None
        
        # Обновляем атрибуты модели
        for key, value in model_data.items():
            if hasattr(model_instance, key):
                setattr(model_instance, key, value)
        
        await self.db.flush()
        await self.db.refresh(model_instance)
        return model_instance
    
    async def delete(self, model_id: UUID, soft_delete: bool = True) -> bool:
        """
        Удаление записи (фактическое или мягкое).
        
        Args:
            model_id: Идентификатор модели
            soft_delete: Если True, выполняется мягкое удаление (is_active = False)
                        Если False, запись полностью удаляется из базы
            
        Returns:
            True если запись успешно удалена, иначе False
        """
        model_instance = await self.get_by_id(model_id)
        if not model_instance:
            return False
        
        if soft_delete:
            # Мягкое удаление через установку флага is_active=False
            if hasattr(model_instance, "is_active"):
                model_instance.is_active = False
                await self.db.flush()
            else:
                # Если у модели нет is_active, делаем физическое удаление
                await self.db.delete(model_instance)
        else:
            # Физическое удаление
            await self.db.delete(model_instance)
        
        await self.db.flush()
        return True
    
    async def list(self, 
                   filters: Optional[Dict[str, Any]] = None, 
                   pagination: Optional[Dict[str, int]] = None, 
                   order_by: Optional[List[str]] = None) -> List[T]:
        """
        Получение списка записей с фильтрацией, пагинацией и сортировкой.
        
        Args:
            filters: Словарь с условиями фильтрации {field_name: value} или {field_name: {'op': 'eq', 'value': value}}
            pagination: Словарь с параметрами пагинации {'skip': int, 'limit': int}
            order_by: Список полей для сортировки ["field_name", "-field_name"] (префикс - для сортировки по убыванию)
            
        Returns:
            Список найденных моделей
        """
        query = select(self.model)
        
        # Применяем фильтры
        if filters:
            for field_name, value in filters.items():
                if hasattr(self.model, field_name):
                    if isinstance(value, dict) and 'op' in value:
                        op = value['op']
                        val = value['value']
                        field = getattr(self.model, field_name)
                        
                        if op == 'eq':
                            query = query.where(field == val)
                        elif op == 'ne':
                            query = query.where(field != val)
                        elif op == 'gt':
                            query = query.where(field > val)
                        elif op == 'lt':
                            query = query.where(field < val)
                        elif op == 'ge':
                            query = query.where(field >= val)
                        elif op == 'le':
                            query = query.where(field <= val)
                        elif op == 'like':
                            query = query.where(field.like(f"%{val}%"))
                        elif op == 'in':
                            query = query.where(field.in_(val))
                    else:
                        query = query.where(getattr(self.model, field_name) == value)
        
        # Применяем сортировку
        if order_by:
            for field_name in order_by:
                if field_name.startswith('-'):
                    # Сортировка по убыванию
                    field_name = field_name[1:]
                    if hasattr(self.model, field_name):
                        query = query.order_by(getattr(self.model, field_name).desc())
                else:
                    # Сортировка по возрастанию
                    if hasattr(self.model, field_name):
                        query = query.order_by(getattr(self.model, field_name).asc())
        
        # Применяем пагинацию
        if pagination:
            skip = pagination.get('skip', 0)
            limit = pagination.get('limit', 100)
            query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Подсчет количества записей с опциональной фильтрацией.
        
        Args:
            filters: Словарь с условиями фильтрации {field_name: value}
            
        Returns:
            Количество записей
        """
        query = select(func.count()).select_from(self.model)
        
        # Применяем фильтры
        if filters:
            for field_name, value in filters.items():
                if hasattr(self.model, field_name):
                    if isinstance(value, dict) and 'op' in value:
                        op = value['op']
                        val = value['value']
                        field = getattr(self.model, field_name)
                        
                        if op == 'eq':
                            query = query.where(field == val)
                        elif op == 'ne':
                            query = query.where(field != val)
                        elif op == 'gt':
                            query = query.where(field > val)
                        elif op == 'lt':
                            query = query.where(field < val)
                        elif op == 'ge':
                            query = query.where(field >= val)
                        elif op == 'le':
                            query = query.where(field <= val)
                        elif op == 'like':
                            query = query.where(field.like(f"%{val}%"))
                        elif op == 'in':
                            query = query.where(field.in_(val))
                    else:
                        query = query.where(getattr(self.model, field_name) == value)
        
        result = await self.db.execute(query)
        return result.scalar()