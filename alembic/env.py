"""
Alembic environment script для управления миграциями базы данных.
Поддерживает асинхронную работу с SQLAlchemy и автоматически
загружает все модели приложения.
"""
import asyncio
import logging
import os
import sys
from logging.config import fileConfig
from typing import List

from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Загружаем переменные окружения
load_dotenv(override=True)

# Добавляем корневую директорию проекта в sys.path для корректного импорта
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# Импортируем Base и настройки подключения к БД
from app.core.database.postgresql import Base
from app.config import settings

# Импортируем все модели, чтобы они были доступны для автогенерации миграций
# Используем импорты из __init__.py модуля models для поддержки всех моделей
from app.models import (
    BaseModel, User, ActivityType, ActivitySubtype, NeedCategory, Need,
    Activity, ActivityEvaluation, ActivityNeed, UserCalendar, ActivitySchedule,
    UserNeed, UserNeedHistory, NeedFulfillmentPlan, NeedFulfillmentObjective,
    UserState, Exercise, Test, Practice, UserExerciseProgress
)

# Настройка логирования
logger = logging.getLogger("alembic.env")

# Получаем конфигурацию из alembic.ini
config = context.config

# Устанавливаем URL для подключения к базе данных из переменных окружения
# Используем асинхронную версию PostgreSQL URL с asyncpg
try:
    db_url = str(settings.postgres.DATABASE_URL)
    # Убедимся, что URL использует asyncpg драйвер
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
    config.set_main_option("sqlalchemy.url", db_url)
    logger.info(f"Using database URL: {db_url}")
except Exception as e:
    logger.error(f"Error setting database URL: {e}")
    # Если URL не установлен, используем URL из alembic.ini (но это должно быть предупреждение)
    logger.warning("Using default URL from alembic.ini")

# Настраиваем логирование из конфигурационного файла
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Устанавливаем metadata для автогенерации миграций
target_metadata = Base.metadata

# Конфигурация для сравнения схемы
# Эти настройки управляют тем, как alembic сравнивает текущую схему с метаданными
config_kwargs = {
    "target_metadata": target_metadata,
    "include_schemas": True,
    "include_name": True,
    "compare_type": True,      # Сравнивать типы колонок
    "compare_server_default": True,  # Сравнивать значения по умолчанию
    "render_as_batch": True,   # Использовать batch для SQLite
}


def get_exclude_tables() -> List[str]:
    """
    Получает список таблиц, которые нужно исключить из автогенерации миграций.
    """
    # Например, можно исключить таблицы для тестов, временные таблицы и т.д.
    return []


def include_object(object, name, type_, reflected, compare_to):
    """
    Функция, определяющая, включать ли объект в миграцию.
    
    Args:
        object: SQL-объект (таблица, индекс и т.д.)
        name: Имя объекта
        type_: Тип объекта (table, column, index и т.д.)
        reflected: True, если объект получен из БД, False если из метаданных
        compare_to: Объект для сравнения, или None
        
    Returns:
        bool: True, если объект нужно включить в миграцию, иначе False
    """
    # Исключаем определенные таблицы
    if type_ == "table" and name in get_exclude_tables():
        return False
    return True


def run_migrations_offline() -> None:
    """
    Запускает миграции в 'offline' режиме.
    
    В этом режиме мы не создаем движок, а просто генерируем SQL-команды.
    Полезно для генерации SQL-скриптов для ручного применения.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        **config_kwargs
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    Выполняет миграции с использованием соединения с БД.
    
    Args:
        connection: Соединение с базой данных
    """
    context.configure(
        connection=connection,
        include_object=include_object,
        **config_kwargs
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    Запускает миграции в 'online' режиме асинхронно.
    
    Создает движок и соединение с БД для применения миграций.
    """
    # Создаем движок с настройкой пула соединений
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    # Создаем соединение и выполняем миграции
    async with connectable.connect() as connection:
        # Выполняем миграции в синхронном контексте
        await connection.run_sync(do_run_migrations)

    # Корректно закрываем соединение с БД
    await connectable.dispose()


# Запускаем миграции в соответствующем режиме
if context.is_offline_mode():
    logger.info("Running migrations in offline mode")
    run_migrations_offline()
else:
    logger.info("Running migrations in online mode")
    asyncio.run(run_migrations_online())