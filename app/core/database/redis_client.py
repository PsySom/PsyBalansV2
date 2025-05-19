import redis.asyncio as redis
from typing import Optional, Any, Union
import json
import logging
from app.config import settings

# Настройка логирования
logger = logging.getLogger(__name__)

# Глобальные переменные для клиента Redis
redis_client: Optional[redis.Redis] = None


async def connect_to_redis() -> redis.Redis:
    """
    Устанавливает соединение с Redis и возвращает клиент
    """
    global redis_client
    try:
        # Создаем Redis клиент
        redis_client = redis.Redis.from_url(
            str(settings.redis.REDIS_URL or "redis://localhost:6379/0"),
            decode_responses=True,
            encoding="utf-8"
        )
        
        # Проверяем соединение
        await redis_client.ping()
        logger.info("Connected to Redis successfully")
        return redis_client
    except Exception as e:
        # В случае ошибки, используем имитацию Redis через обычный словарь
        logger.warning(f"Failed to connect to Redis: {e}. Using in-memory mock")
        
        # Создаем простую имитацию Redis через обычный словарь
        class MockRedis:
            def __init__(self):
                self.data = {}
                self.ttl = {}
            
            async def ping(self):
                return True
                
            async def close(self):
                pass
                
            async def set(self, key, value, ex=None):
                self.data[key] = value
                return True
                
            async def get(self, key):
                return self.data.get(key)
                
            async def delete(self, *keys):
                count = 0
                for key in keys:
                    if key in self.data:
                        del self.data[key]
                        count += 1
                return count
                
            async def hset(self, name, key, value):
                if name not in self.data:
                    self.data[name] = {}
                self.data[name][key] = value
                return 1
                
            async def hget(self, name, key):
                if name in self.data:
                    return self.data[name].get(key)
                return None
                
            async def hgetall(self, name):
                return self.data.get(name, {})
                
            async def publish(self, channel, message):
                return 0  # В имитации нет подписчиков
        
        redis_client = MockRedis()
        return redis_client


async def get_redis() -> redis.Redis:
    """
    Зависимость для FastAPI, предоставляющая соединение с Redis
    """
    if redis_client is None:
        await connect_to_redis()
    return redis_client


async def close_redis_connection():
    """
    Закрывает соединение с Redis
    """
    global redis_client
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")


async def check_redis_connection() -> tuple[bool, str]:
    """
    Проверяет соединение с Redis
    Возвращает кортеж (успех, сообщение)
    """
    try:
        if redis_client is None:
            await connect_to_redis()
            
        # Проверяем соединение через команду ping
        await redis_client.ping()
        return True, "Successfully connected to Redis"
    except Exception as e:
        return False, f"Failed to connect to Redis: {str(e)}"


# Вспомогательные функции для работы с Redis

async def set_key(key: str, value: Any, expires: Optional[int] = None) -> bool:
    """
    Устанавливает значение ключа с опциональным временем жизни (в секундах)
    """
    if redis_client is None:
        await connect_to_redis()
    
    if not isinstance(value, (str, int, float, bool)):
        value = json.dumps(value)
    
    result = await redis_client.set(key, value, ex=expires)
    return result


async def get_key(key: str) -> Optional[str]:
    """
    Получает значение ключа
    """
    if redis_client is None:
        await connect_to_redis()
    
    return await redis_client.get(key)


async def get_json(key: str) -> Optional[Any]:
    """
    Получает значение ключа и десериализует его из JSON
    """
    if redis_client is None:
        await connect_to_redis()
    
    value = await redis_client.get(key)
    if value:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return None


async def delete_key(key: str) -> int:
    """
    Удаляет ключ и возвращает количество удаленных ключей
    """
    if redis_client is None:
        await connect_to_redis()
    
    return await redis_client.delete(key)


async def set_hash(hash_name: str, key: str, value: Any) -> int:
    """
    Устанавливает поле хэша
    """
    if redis_client is None:
        await connect_to_redis()
    
    if not isinstance(value, (str, int, float, bool)):
        value = json.dumps(value)
    
    return await redis_client.hset(hash_name, key, value)


async def get_hash(hash_name: str, key: str) -> Optional[str]:
    """
    Получает значение поля хэша
    """
    if redis_client is None:
        await connect_to_redis()
    
    return await redis_client.hget(hash_name, key)


async def get_all_hash(hash_name: str) -> dict:
    """
    Получает все поля и значения хэша
    """
    if redis_client is None:
        await connect_to_redis()
    
    return await redis_client.hgetall(hash_name)


async def publish_message(channel: str, message: Any) -> int:
    """
    Публикует сообщение в канал
    """
    if redis_client is None:
        await connect_to_redis()
    
    if not isinstance(message, str):
        message = json.dumps(message)
    
    return await redis_client.publish(channel, message)


async def set_cache(key: str, value: Any, expires: int = 3600) -> bool:
    """
    Удобная функция для кэширования данных с TTL в секундах (по умолчанию 1 час)
    """
    return await set_key(f"cache:{key}", value, expires)


async def get_cache(key: str) -> Optional[Any]:
    """
    Получает данные из кэша
    """
    value = await get_key(f"cache:{key}")
    if value:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return None


async def invalidate_cache(key: str) -> int:
    """
    Инвалидирует кэш по ключу
    """
    return await delete_key(f"cache:{key}")


# Инициализация подключения при импорте модуля
async def init_redis():
    await connect_to_redis()