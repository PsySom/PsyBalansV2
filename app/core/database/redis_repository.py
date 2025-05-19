"""
Репозиторий для работы с Redis.
Предоставляет абстракцию для выполнения операций с кэшем в Redis.
"""
import json
import logging
from typing import Any, Dict, List, Optional, Set, Union
import redis.asyncio as redis

from app.core.database.redis_client import get_redis

logger = logging.getLogger(__name__)

class RedisRepository:
    """
    Репозиторий для работы с Redis.
    Предоставляет методы для работы с кэшем, хранения и получения структурированных данных,
    а также управления временем жизни ключей.
    """
    
    def __init__(self, prefix: str = ""):
        """
        Инициализирует репозиторий с опциональным префиксом для ключей.
        
        Args:
            prefix: Префикс, который будет добавляться к ключам
        """
        self.prefix = prefix
    
    async def _get_redis(self) -> redis.Redis:
        """
        Получает объект клиента Redis.
        
        Returns:
            redis.Redis: Объект клиента Redis
        """
        return await get_redis()
    
    def _format_key(self, key: str) -> str:
        """
        Форматирует ключ с префиксом, если он задан.
        
        Args:
            key: Исходный ключ
            
        Returns:
            str: Отформатированный ключ с префиксом
        """
        if self.prefix:
            return f"{self.prefix}:{key}"
        return key
    
    def _format_user_key(self, user_id: str, key: str) -> str:
        """
        Форматирует ключ для конкретного пользователя.
        
        Args:
            user_id: Идентификатор пользователя
            key: Исходный ключ
            
        Returns:
            str: Отформатированный ключ для пользователя
        """
        if self.prefix:
            return f"{self.prefix}:user:{user_id}:{key}"
        return f"user:{user_id}:{key}"
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Устанавливает значение по ключу с опциональным временем жизни.
        
        Args:
            key: Ключ
            value: Значение (будет сериализовано в JSON, если это не примитивный тип)
            ttl: Время жизни в секундах (опционально)
            
        Returns:
            bool: True, если операция успешна
            
        Raises:
            Exception: При ошибке соединения с Redis
        """
        try:
            redis_client = await self._get_redis()
            formatted_key = self._format_key(key)
            
            # Сериализуем сложные типы данных
            if not isinstance(value, (str, int, float, bool, bytes, type(None))):
                value = json.dumps(value)
            
            return await redis_client.set(formatted_key, value, ex=ttl)
        except Exception as e:
            logger.error(f"Error setting value in Redis for key {key}: {e}")
            raise
    
    async def get(self, key: str, default: Any = None) -> Any:
        """
        Получает значение по ключу.
        
        Args:
            key: Ключ
            default: Значение по умолчанию, если ключа нет
            
        Returns:
            Any: Значение из Redis или default
            
        Raises:
            Exception: При ошибке соединения с Redis
        """
        try:
            redis_client = await self._get_redis()
            formatted_key = self._format_key(key)
            
            value = await redis_client.get(formatted_key)
            
            if value is None:
                return default
            
            # Пробуем десериализовать JSON, если это возможно
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                # Если не получилось десериализовать, возвращаем как есть
                return value
        except Exception as e:
            logger.error(f"Error getting value from Redis for key {key}: {e}")
            raise
    
    async def delete(self, key: str) -> int:
        """
        Удаляет ключ из Redis.
        
        Args:
            key: Ключ
            
        Returns:
            int: Количество удаленных ключей (0 или 1)
            
        Raises:
            Exception: При ошибке соединения с Redis
        """
        try:
            redis_client = await self._get_redis()
            formatted_key = self._format_key(key)
            
            return await redis_client.delete(formatted_key)
        except Exception as e:
            logger.error(f"Error deleting key from Redis: {key}: {e}")
            raise
    
    async def exists(self, key: str) -> bool:
        """
        Проверяет существование ключа в Redis.
        
        Args:
            key: Ключ
            
        Returns:
            bool: True, если ключ существует
            
        Raises:
            Exception: При ошибке соединения с Redis
        """
        try:
            redis_client = await self._get_redis()
            formatted_key = self._format_key(key)
            
            return await redis_client.exists(formatted_key) > 0
        except Exception as e:
            logger.error(f"Error checking existence of key in Redis: {key}: {e}")
            raise
    
    async def incr(self, key: str, amount: int = 1) -> int:
        """
        Увеличивает значение ключа на указанное число.
        
        Args:
            key: Ключ
            amount: Значение для инкремента (по умолчанию 1)
            
        Returns:
            int: Новое значение ключа
            
        Raises:
            Exception: При ошибке соединения с Redis
        """
        try:
            redis_client = await self._get_redis()
            formatted_key = self._format_key(key)
            
            if amount == 1:
                return await redis_client.incr(formatted_key)
            else:
                return await redis_client.incrby(formatted_key, amount)
        except Exception as e:
            logger.error(f"Error incrementing value in Redis for key {key}: {e}")
            raise
    
    async def expire(self, key: str, ttl: int) -> bool:
        """
        Устанавливает время жизни для существующего ключа.
        
        Args:
            key: Ключ
            ttl: Время жизни в секундах
            
        Returns:
            bool: True, если TTL был установлен
            
        Raises:
            Exception: При ошибке соединения с Redis
        """
        try:
            redis_client = await self._get_redis()
            formatted_key = self._format_key(key)
            
            return await redis_client.expire(formatted_key, ttl)
        except Exception as e:
            logger.error(f"Error setting TTL for key in Redis: {key}: {e}")
            raise
    
    async def ttl(self, key: str) -> int:
        """
        Получает оставшееся время жизни ключа.
        
        Args:
            key: Ключ
            
        Returns:
            int: Время жизни в секундах (-2, если ключа нет, -1, если TTL не установлен)
            
        Raises:
            Exception: При ошибке соединения с Redis
        """
        try:
            redis_client = await self._get_redis()
            formatted_key = self._format_key(key)
            
            return await redis_client.ttl(formatted_key)
        except Exception as e:
            logger.error(f"Error getting TTL for key in Redis: {key}: {e}")
            raise
    
    async def set_dict(self, key: str, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        Сохраняет словарь в Redis.
        
        Args:
            key: Ключ
            data: Словарь для сохранения
            ttl: Время жизни в секундах (опционально)
            
        Returns:
            bool: True, если операция успешна
            
        Raises:
            Exception: При ошибке соединения с Redis
        """
        return await self.set(key, data, ttl)
    
    async def get_dict(self, key: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Получает словарь из Redis.
        
        Args:
            key: Ключ
            default: Значение по умолчанию, если ключа нет
            
        Returns:
            Dict[str, Any]: Словарь из Redis или default
            
        Raises:
            Exception: При ошибке соединения с Redis
        """
        result = await self.get(key, default)
        if result is not None and not isinstance(result, dict):
            return default or {}
        return result
    
    async def set_list(self, key: str, data: List[Any], ttl: Optional[int] = None) -> bool:
        """
        Сохраняет список в Redis.
        
        Args:
            key: Ключ
            data: Список для сохранения
            ttl: Время жизни в секундах (опционально)
            
        Returns:
            bool: True, если операция успешна
            
        Raises:
            Exception: При ошибке соединения с Redis
        """
        return await self.set(key, data, ttl)
    
    async def get_list(self, key: str, default: Optional[List[Any]] = None) -> List[Any]:
        """
        Получает список из Redis.
        
        Args:
            key: Ключ
            default: Значение по умолчанию, если ключа нет
            
        Returns:
            List[Any]: Список из Redis или default
            
        Raises:
            Exception: При ошибке соединения с Redis
        """
        result = await self.get(key, default)
        if result is not None and not isinstance(result, list):
            return default or []
        return result
    
    async def hset(self, hash_key: str, field: str, value: Any) -> int:
        """
        Устанавливает поле в хеше.
        
        Args:
            hash_key: Ключ хеша
            field: Поле в хеше
            value: Значение
            
        Returns:
            int: 1, если поле было создано, 0, если обновлено
            
        Raises:
            Exception: При ошибке соединения с Redis
        """
        try:
            redis_client = await self._get_redis()
            formatted_key = self._format_key(hash_key)
            
            # Сериализуем сложные типы данных
            if not isinstance(value, (str, int, float, bool, bytes, type(None))):
                value = json.dumps(value)
            
            return await redis_client.hset(formatted_key, field, value)
        except Exception as e:
            logger.error(f"Error setting hash field in Redis: {hash_key}:{field}: {e}")
            raise
    
    async def hget(self, hash_key: str, field: str, default: Any = None) -> Any:
        """
        Получает значение поля из хеша.
        
        Args:
            hash_key: Ключ хеша
            field: Поле в хеше
            default: Значение по умолчанию, если поля нет
            
        Returns:
            Any: Значение из Redis или default
            
        Raises:
            Exception: При ошибке соединения с Redis
        """
        try:
            redis_client = await self._get_redis()
            formatted_key = self._format_key(hash_key)
            
            value = await redis_client.hget(formatted_key, field)
            
            if value is None:
                return default
            
            # Пробуем десериализовать JSON, если это возможно
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                # Если не получилось десериализовать, возвращаем как есть
                return value
        except Exception as e:
            logger.error(f"Error getting hash field from Redis: {hash_key}:{field}: {e}")
            raise
    
    async def hgetall(self, hash_key: str) -> Dict[str, Any]:
        """
        Получает все поля и значения хеша.
        
        Args:
            hash_key: Ключ хеша
            
        Returns:
            Dict[str, Any]: Словарь с полями и значениями
            
        Raises:
            Exception: При ошибке соединения с Redis
        """
        try:
            redis_client = await self._get_redis()
            formatted_key = self._format_key(hash_key)
            
            result = await redis_client.hgetall(formatted_key)
            
            # Пробуем десериализовать JSON значения
            for key, value in result.items():
                try:
                    result[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    # Оставляем как есть, если не получилось десериализовать
                    pass
            
            return result
        except Exception as e:
            logger.error(f"Error getting all hash fields from Redis: {hash_key}: {e}")
            raise
    
    async def hdel(self, hash_key: str, field: str) -> int:
        """
        Удаляет поле из хеша.
        
        Args:
            hash_key: Ключ хеша
            field: Поле в хеше
            
        Returns:
            int: 1, если поле было удалено, 0, если поля не было
            
        Raises:
            Exception: При ошибке соединения с Redis
        """
        try:
            redis_client = await self._get_redis()
            formatted_key = self._format_key(hash_key)
            
            return await redis_client.hdel(formatted_key, field)
        except Exception as e:
            logger.error(f"Error deleting hash field from Redis: {hash_key}:{field}: {e}")
            raise
    
    async def hincrby(self, hash_key: str, field: str, amount: int = 1) -> int:
        """
        Увеличивает значение поля хеша на указанное число.
        
        Args:
            hash_key: Ключ хеша
            field: Поле в хеше
            amount: Значение для инкремента (по умолчанию 1)
            
        Returns:
            int: Новое значение поля
            
        Raises:
            Exception: При ошибке соединения с Redis
        """
        try:
            redis_client = await self._get_redis()
            formatted_key = self._format_key(hash_key)
            
            return await redis_client.hincrby(formatted_key, field, amount)
        except Exception as e:
            logger.error(f"Error incrementing hash field in Redis: {hash_key}:{field}: {e}")
            raise
    
    async def set_user_data(self, user_id: str, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Сохраняет данные для конкретного пользователя.
        
        Args:
            user_id: Идентификатор пользователя
            key: Ключ данных
            value: Значение для сохранения
            ttl: Время жизни в секундах (опционально)
            
        Returns:
            bool: True, если операция успешна
            
        Raises:
            Exception: При ошибке соединения с Redis
        """
        formatted_key = self._format_user_key(user_id, key)
        return await self.set(formatted_key, value, ttl)
    
    async def get_user_data(self, user_id: str, key: str, default: Any = None) -> Any:
        """
        Получает данные для конкретного пользователя.
        
        Args:
            user_id: Идентификатор пользователя
            key: Ключ данных
            default: Значение по умолчанию, если данных нет
            
        Returns:
            Any: Данные из Redis или default
            
        Raises:
            Exception: При ошибке соединения с Redis
        """
        formatted_key = self._format_user_key(user_id, key)
        return await self.get(formatted_key, default)
    
    async def delete_user_data(self, user_id: str, key: str) -> int:
        """
        Удаляет данные для конкретного пользователя.
        
        Args:
            user_id: Идентификатор пользователя
            key: Ключ данных
            
        Returns:
            int: Количество удаленных ключей (0 или 1)
            
        Raises:
            Exception: При ошибке соединения с Redis
        """
        formatted_key = self._format_user_key(user_id, key)
        return await self.delete(formatted_key)
    
    async def clear_user_cache(self, user_id: str) -> int:
        """
        Очищает весь кэш для пользователя.
        
        Args:
            user_id: Идентификатор пользователя
            
        Returns:
            int: Количество удаленных ключей
            
        Raises:
            Exception: При ошибке соединения с Redis
        """
        try:
            redis_client = await self._get_redis()
            
            # Шаблон для ключей пользователя
            user_pattern = self._format_user_key(user_id, "*")
            
            # Ищем все ключи, соответствующие шаблону
            keys = await redis_client.keys(user_pattern)
            
            # Если ключей нет, возвращаем 0
            if not keys:
                return 0
            
            # Удаляем все найденные ключи
            return await redis_client.delete(*keys)
        except Exception as e:
            logger.error(f"Error clearing user cache for user {user_id}: {e}")
            raise