"""
Модуль, отвечающий за инициализацию базы данных и выполнение задач при запуске приложения.
"""

import logging
import asyncio
from app.config import settings
from app.core.database.postgresql import get_db_context, create_tables
from app.core.database.seeds import seed_all
from app.core.database.retry import configure_default_retry

logger = logging.getLogger(__name__)


async def initialize_retry_config() -> None:
    """
    Инициализирует конфигурацию механизма повторных попыток
    на основе настроек приложения.
    """
    retry_settings = settings.retry
    
    logger.info("Инициализация глобальной конфигурации повторных попыток...")
    
    configure_default_retry(
        max_attempts=retry_settings.MAX_ATTEMPTS,
        base_delay=retry_settings.BASE_DELAY,
        max_delay=retry_settings.MAX_DELAY,
        jitter=retry_settings.JITTER,
        timeout=retry_settings.TIMEOUT
    )
    
    logger.info(
        f"Глобальная конфигурация повторных попыток инициализирована: "
        f"max_attempts={retry_settings.MAX_ATTEMPTS}, "
        f"base_delay={retry_settings.BASE_DELAY}, "
        f"max_delay={retry_settings.MAX_DELAY}, "
        f"jitter={retry_settings.JITTER}, "
        f"timeout={retry_settings.TIMEOUT or 'None'}"
    )


async def initialize_database():
    """
    Инициализирует базу данных при запуске приложения:
    1. Инициализирует механизм повторных попыток
    2. Создает таблицы, если они не существуют
    3. Заполняет базу данных начальными значениями
    """
    try:
        # Инициализируем механизм повторных попыток
        await initialize_retry_config()
        
        # Создаем таблицы в базе данных
        await create_tables()
        logger.info("Таблицы базы данных созданы или уже существуют")
        
        # Заполняем базу данных начальными значениями
        async with get_db_context() as db:
            await seed_all(db)
        
        logger.info("База данных успешно инициализирована")
        return True
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        return False


# Функция, которая может быть вызвана из командной строки для инициализации БД
def init_db_sync():
    """
    Синхронная функция для инициализации базы данных.
    Может быть вызвана из командной строки.
    """
    asyncio.run(initialize_database())