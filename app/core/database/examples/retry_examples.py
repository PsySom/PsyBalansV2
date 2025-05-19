"""
Примеры использования механизма повторных попыток с базами данных.
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import OperationalError

from app.core.database import (
    RetryConfig, with_retry, default_retry_config, configure_default_retry
)
from app.core.database.postgresql import get_db
from app.core.database.mongodb import get_mongodb
from app.core.database.redis_client import get_redis
from app.core.exceptions.database import ConnectionError, QueryError

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app.examples.retry")


# Пример 1: Использование декоратора с настройками по умолчанию
@with_retry
async def example_postgres_query_default() -> List[Dict[str, Any]]:
    """
    Пример выполнения запроса к PostgreSQL с повторными попытками
    по настройкам по умолчанию.
    """
    async for db in get_db():
        result = await db.execute("SELECT * FROM users LIMIT 10")
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]
    return []


# Пример 2: Настройка параметров повторных попыток напрямую
@with_retry(max_attempts=5, base_delay=0.2, max_delay=5.0)
async def example_postgres_query_custom() -> List[Dict[str, Any]]:
    """
    Пример выполнения запроса к PostgreSQL с настраиваемыми параметрами повторных попыток.
    """
    async for db in get_db():
        result = await db.execute("SELECT * FROM users LIMIT 10")
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]
    return []


# Пример 3: Использование объекта RetryConfig
custom_config = RetryConfig(
    max_attempts=4,
    base_delay=0.5,
    max_delay=8.0,
    jitter=0.2,
    retry_exceptions=[ConnectionError, QueryError, OperationalError],
    timeout=15.0
)

@with_retry(retry_config=custom_config)
async def example_postgres_query_with_config() -> List[Dict[str, Any]]:
    """
    Пример выполнения запроса к PostgreSQL с объектом RetryConfig.
    """
    async for db in get_db():
        result = await db.execute("SELECT * FROM users LIMIT 10")
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]
    return []


# Пример 4: Использование с MongoDB
@with_retry(max_attempts=3, base_delay=0.3)
async def example_mongodb_query() -> List[Dict[str, Any]]:
    """
    Пример выполнения запроса к MongoDB с повторными попытками.
    """
    db = await get_mongodb()
    collection = db["users"]
    cursor = collection.find({}).limit(10)
    return await cursor.to_list(length=10)


# Пример 5: Использование с Redis
@with_retry
async def example_redis_operation(key: str) -> Optional[str]:
    """
    Пример операции с Redis с повторными попытками.
    """
    redis = await get_redis()
    return await redis.get(key)


# Пример 6: Имитация временной ошибки для демонстрации повторных попыток
attempt_counter = 0

@with_retry(max_attempts=5, base_delay=0.1)
async def example_with_simulated_errors() -> str:
    """
    Пример функции, которая имитирует временные ошибки
    для демонстрации механизма повторных попыток.
    """
    global attempt_counter
    attempt_counter += 1
    
    # Первые 3 вызова вызывают ошибку, затем функция работает нормально
    if attempt_counter <= 3:
        logger.info(f"Симулируем ошибку в попытке {attempt_counter}")
        if attempt_counter == 1:
            raise ConnectionError("Симулированная ошибка соединения")
        elif attempt_counter == 2:
            raise QueryError("Симулированная ошибка запроса")
        else:
            raise OperationalError("timeout exceeded", "", "")
    
    logger.info(f"Успешное выполнение в попытке {attempt_counter}")
    return "Успешно выполнено после нескольких попыток"


# Пример 7: Настройка глобальной конфигурации повторных попыток
async def example_configure_global_config() -> None:
    """
    Пример настройки глобальной конфигурации повторных попыток.
    """
    # Получаем текущую глобальную конфигурацию
    logger.info(f"Текущая глобальная конфигурация: {default_retry_config.to_dict()}")
    
    # Настраиваем глобальную конфигурацию
    configure_default_retry(
        max_attempts=4,
        base_delay=0.3,
        max_delay=6.0,
        jitter=0.15,
        timeout=12.0
    )
    
    # Проверяем новую конфигурацию
    logger.info(f"Обновленная глобальная конфигурация: {default_retry_config.to_dict()}")
    
    # Эта функция будет использовать обновленную глобальную конфигурацию
    @with_retry
    async def function_with_updated_defaults() -> str:
        return "Функция с обновленной конфигурацией по умолчанию"


# Функция для запуска примеров
async def run_examples() -> None:
    """
    Запускает примеры использования механизма повторных попыток.
    """
    logger.info("Запуск примеров механизма повторных попыток...")
    
    # Пример с имитацией ошибок для демонстрации повторных попыток
    try:
        result = await example_with_simulated_errors()
        logger.info(f"Результат: {result}")
    except Exception as e:
        logger.error(f"Ошибка при выполнении примера: {e}")
    
    # Сбрасываем счетчик попыток для следующих тестов
    global attempt_counter
    attempt_counter = 0
    
    # Пример настройки глобальной конфигурации
    await example_configure_global_config()


# Точка входа для запуска примеров
if __name__ == "__main__":
    asyncio.run(run_examples())