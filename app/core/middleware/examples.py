"""
Примеры использования middleware для логирования.
"""
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient

from app.core.database import get_db
from app.config import settings
from app.core.middleware.database import (
    DatabaseLoggerMiddleware, log_db_operation, setup_db_logging
)
from app.core.middleware.mongodb import (
    MongoDBLoggerMiddleware, log_mongodb_operation, setup_mongodb_logging
)
from app.core.middleware.http import LoggingMiddleware, add_logging_middleware


def setup_logging_middleware_example():
    """
    Пример настройки всех middleware в приложении FastAPI.
    """
    # Создаем приложение FastAPI
    app = FastAPI()
    
    # 1. Настройка логирования HTTP-запросов
    add_logging_middleware(
        app=app,
        log_all_requests=not settings.DEBUG,  # В продакшене логируем только ошибки и медленные запросы
        log_request_body=True,
        log_response_body=True,
        exclude_paths=["/health", "/metrics", "/docs", "/openapi.json"],
        exclude_extensions=[".js", ".css", ".ico", ".png", ".jpg"],
        max_body_length=10000,
        slow_request_threshold=1.0,  # Запросы дольше 1 секунды считаются медленными
        request_id_header="X-Request-ID"
    )
    
    # 2. Настройка логирования операций с PostgreSQL
    # Получаем движок SQLAlchemy
    postgres_engine = create_async_engine(str(settings.postgres.DATABASE_URL))
    
    # Настраиваем middleware для логирования SQL-запросов
    db_logger = setup_db_logging(
        engine=postgres_engine,
        slow_query_threshold=1.0,  # Запросы дольше 1 секунды считаются медленными
        log_level="DEBUG" if settings.DEBUG else "INFO"
    )
    
    # 3. Настройка логирования операций с MongoDB
    # Создаем клиент MongoDB
    mongodb_client = AsyncIOMotorClient(
        settings.mongodb.MONGODB_URL,
        serverSelectionTimeoutMS=5000
    )
    
    # Настраиваем middleware для логирования операций с MongoDB
    mongodb_logger = setup_mongodb_logging(
        client=mongodb_client,
        slow_query_threshold=1.0,  # Запросы дольше 1 секунды считаются медленными
        log_level="DEBUG" if settings.DEBUG else "INFO"
    )
    
    return app


# Пример использования декоратора log_db_operation с репозиторием PostgreSQL
class UserRepository:
    """
    Пример репозитория с использованием декоратора log_db_operation.
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    @log_db_operation(operation_name="get_user_by_id")
    async def get_user_by_id(self, user_id: int):
        """
        Получает пользователя по ID с логированием операции.
        """
        # Пример запроса к базе данных
        query = "SELECT * FROM users WHERE id = :user_id"
        result = await self.db.execute(query, {"user_id": user_id})
        return result.fetchone()
    
    @log_db_operation(operation_name="create_user")
    async def create_user(self, user_data):
        """
        Создает пользователя с логированием операции.
        """
        # Пример запроса к базе данных
        query = """
            INSERT INTO users (username, email, password)
            VALUES (:username, :email, :password)
            RETURNING id
        """
        result = await self.db.execute(query, user_data)
        await self.db.commit()
        return result.fetchone()[0]


# Пример использования декоратора log_mongodb_operation с репозиторием MongoDB
class ActivityRepository:
    """
    Пример репозитория с использованием декоратора log_mongodb_operation.
    """
    
    def __init__(self, client: AsyncIOMotorClient):
        self.db = client[settings.mongodb.MONGODB_DB_NAME]
        self.collection = self.db.activities
    
    @log_mongodb_operation(operation_name="get_activity_by_id")
    async def get_activity_by_id(self, activity_id: str):
        """
        Получает активность по ID с логированием операции.
        """
        return await self.collection.find_one({"_id": activity_id})
    
    @log_mongodb_operation(operation_name="create_activity")
    async def create_activity(self, activity_data):
        """
        Создает активность с логированием операции.
        """
        result = await self.collection.insert_one(activity_data)
        return result.inserted_id


# Пример FastAPI-зависимости для получения репозиториев с логированием
async def get_user_repository(db: AsyncSession = Depends(get_db)):
    return UserRepository(db)


async def get_activity_repository(client: AsyncIOMotorClient = Depends(lambda: AsyncIOMotorClient(settings.mongodb.MONGODB_URL))):
    return ActivityRepository(client)