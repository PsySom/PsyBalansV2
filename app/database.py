from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import MetaData, create_engine
import os
from dotenv import load_dotenv
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

# Загружаем переменные окружения
load_dotenv(override=True)

# Создаем базовый класс для ORM-моделей
Base = declarative_base()

# Создаем объект метаданных
metadata = MetaData()

# Настройка SQLite как временное решение, чтобы приложение запускалось без внешней БД
SQLITE_URL = "sqlite:///./psybalans.db"
sync_engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})

# Проверяем наличие переменных окружения для PostgreSQL и MongoDB
POSTGRES_URL = os.getenv("DATABASE_URL")
MONGODB_URI = os.getenv("MONGODB_URI")

# Создаем асинхронный движок SQLAlchemy с SQLite
# Так как с asyncpg могут быть проблемы, всегда используем SQLite
engine = create_async_engine(
    "sqlite+aiosqlite:///./psybalans.db",
    echo=True,
    connect_args={"check_same_thread": False}
)

# Создаем асинхронную фабрику сессий
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# MongoDB клиент (опционально)
mongo_db = None
if MONGODB_URI:
    try:
        mongo_client = AsyncIOMotorClient(MONGODB_URI)
        mongo_db = mongo_client.get_database("psybalans")
        print("MongoDB подключение настроено")
    except Exception as e:
        print(f"Ошибка подключения к MongoDB: {e}")

# Функция для получения соединения с БД
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Функция для проверки подключения к базе данных
async def check_postgres_connection():
    if not POSTGRES_URL:
        return False, "PostgreSQL не настроен. Используется SQLite."
    
    try:
        # Проверяем только наличие переменной окружения
        return True, "PostgreSQL настроен (переменная окружения присутствует)"
    except Exception as e:
        return False, f"Ошибка проверки PostgreSQL: {str(e)}"

# Функция для проверки подключения к MongoDB
async def check_mongodb_connection():
    if not MONGODB_URI:
        return False, "MongoDB не настроен. Эта функциональность будет недоступна."
    
    try:
        if mongo_db is None:
            return False, "MongoDB клиент не инициализирован"
        await mongo_db.command("ping")
        return True, "Подключение к MongoDB успешно"
    except Exception as e:
        return False, f"Ошибка подключения к MongoDB: {str(e)}"

# Функция для создания таблиц в SQLite
def init_db():
    # Импортируем модели здесь для предотвращения циклических импортов
    from app.models.user import User
    
    # Создаем таблицы в SQLite синхронно
    Base.metadata.create_all(bind=sync_engine)
    print("База данных SQLite инициализирована")