"""
Пример использования механизма повторных попыток с репозиторием.
"""
from typing import List, Optional, Dict, Any, Type, TypeVar
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import OperationalError

from app.models.base import BaseModel
from app.repositories.base_repository import BaseRepository
from app.core.database import with_retry, RetryConfig
from app.core.exceptions.database import ConnectionError, QueryError, DatabaseError

# Определение типа модели
T = TypeVar('T', bound=BaseModel)


class RetryRepository(BaseRepository[T]):
    """
    Пример репозитория с интегрированным механизмом повторных попыток.
    Расширяет BaseRepository, добавляя автоматические повторные попытки
    для всех операций с базой данных.
    """
    
    def __init__(self, db_session: AsyncSession, model_class: Type[T]):
        """
        Инициализация репозитория с сессией базы данных и классом модели.
        
        Args:
            db_session: Асинхронная сессия SQLAlchemy
            model_class: Класс модели SQLAlchemy для этого репозитория
        """
        super().__init__(db_session, model_class)
        
        # Создаем конфигурацию повторных попыток для этого репозитория
        self.retry_config = RetryConfig(
            max_attempts=5,
            base_delay=0.2,
            max_delay=5.0,
            jitter=0.2,
            retry_exceptions=[
                ConnectionError,
                QueryError,
                OperationalError
            ]
        )
    
    @with_retry
    async def create(self, model_data: Dict[str, Any]) -> T:
        """
        Создание новой записи с автоматическими повторными попытками.
        Использует декоратор with_retry с конфигурацией по умолчанию.
        
        Args:
            model_data: Словарь с данными для создания объекта
            
        Returns:
            Созданная модель
        """
        return await super().create(model_data)
    
    @with_retry(max_attempts=3, base_delay=0.1)
    async def get_by_id(self, model_id: UUID) -> Optional[T]:
        """
        Получение записи по идентификатору с автоматическими повторными попытками.
        Использует декоратор with_retry с настраиваемыми параметрами.
        
        Args:
            model_id: Идентификатор модели
            
        Returns:
            Найденная модель или None
        """
        return await super().get_by_id(model_id)
    
    async def update(self, model_id: UUID, model_data: Dict[str, Any]) -> Optional[T]:
        """
        Обновление существующей записи с автоматическими повторными попытками.
        Использует декоратор with_retry с указанным объектом RetryConfig.
        
        Args:
            model_id: Идентификатор модели
            model_data: Словарь с обновленными данными
            
        Returns:
            Обновленная модель или None, если запись не найдена
        """
        # Применяем декоратор динамически к вызову родительского метода
        @with_retry(retry_config=self.retry_config)
        async def _update_with_retry():
            return await super(RetryRepository, self).update(model_id, model_data)
        
        return await _update_with_retry()
    
    async def custom_operation_with_retry_handling(self, model_id: UUID) -> Dict[str, Any]:
        """
        Пример кастомной операции с ручной обработкой повторных попыток.
        
        Args:
            model_id: Идентификатор модели
            
        Returns:
            Данные, полученные из операции
        """
        attempt = 1
        max_attempts = 3
        
        while True:
            try:
                # Выполняем операцию
                instance = await self.get_by_id(model_id)
                if not instance:
                    return {"success": False, "error": "Объект не найден"}
                
                # Другие операции...
                
                return {
                    "success": True,
                    "id": str(instance.id),
                    "data": "Данные, полученные из успешной операции"
                }
            
            except DatabaseError as e:
                # Проверяем, можно ли повторить попытку
                if attempt >= max_attempts:
                    return {
                        "success": False,
                        "error": f"Не удалось выполнить операцию после {attempt} попыток: {str(e)}"
                    }
                
                # Увеличиваем счетчик попыток
                attempt += 1
                
                # Здесь можно добавить задержку между попытками
                # await asyncio.sleep(0.5 * attempt)


# Пример использования в сервисе:
"""
from app.repositories.retry_repository_example import RetryRepository
from app.models.user import User

class UserService:
    def __init__(self, db_session):
        self.user_repo = RetryRepository(db_session, User)
    
    async def create_user(self, user_data):
        # Операция создания пользователя автоматически повторится при временных ошибках
        return await self.user_repo.create(user_data)
    
    async def get_user(self, user_id):
        # Операция получения пользователя автоматически повторится при временных ошибках
        return await self.user_repo.get_by_id(user_id)
"""