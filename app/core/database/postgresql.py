from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from app.config import settings
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

# Настройка логирования
logger = logging.getLogger(__name__)

# Создаем базовый класс для ORM-моделей
Base = declarative_base()

# SQLite для развития (если нет подключения к PostgreSQL)
SQLITE_URL = "sqlite+aiosqlite:///./psybalans.db"

# Создание асинхронного движка
engine = None
AsyncSessionLocal = None


def create_engine_and_session(connection_string: Optional[str] = None):
    """
    Создает движок и сессию на основе строки подключения.
    Если строка не указана, использует настройки из конфигурации
    """
    global engine, AsyncSessionLocal
    
    if connection_string is None:
        try:
            connection_string = str(settings.postgres.DATABASE_URL)
            logger.info("Using PostgreSQL connection")
        except Exception as e:
            logger.warning(f"Could not get PostgreSQL connection URL: {e}")
            connection_string = SQLITE_URL
            logger.info("Falling back to SQLite connection")
    
    # Настройки для PostgreSQL
    if connection_string.startswith("postgresql"):
        engine = create_async_engine(
            connection_string,
            echo=settings.DEBUG,
            future=True,
            pool_size=20,
            max_overflow=10,
        )
    # Настройки для SQLite
    else:
        engine = create_async_engine(
            connection_string,
            echo=settings.DEBUG,
            future=True,
            connect_args={"check_same_thread": False},
        )
    
    # Создаем фабрику асинхронных сессий
    AsyncSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


# Инициализация движка и сессии при импорте модуля
create_engine_and_session()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Зависимость для FastAPI, предоставляющая асинхронную сессию БД
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Контекстный менеджер для использования в асинхронных функциях
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_tables():
    """
    Создает все таблицы в базе данных на основе моделей
    Используется в основном для разработки
    """
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        return False


async def drop_tables():
    """
    Удаляет все таблицы из базы данных
    Используется только для тестирования
    """
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped successfully")
        return True
    except Exception as e:
        logger.error(f"Error dropping database tables: {e}")
        return False


async def check_connection() -> tuple[bool, str]:
    """
    Проверяет соединение с базой данных
    Возвращает кортеж (успех, сообщение)
    """
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        logger.info("Database connection successful")
        return True, "Successfully connected to PostgreSQL"
    except Exception as e:
        error_msg = f"Database connection failed: {e}"
        logger.error(error_msg)
        return False, error_msg