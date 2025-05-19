from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import traceback
import os

from app.config import settings
from app.core.database import (
    get_db, check_postgres_connection, check_mongodb_connection, check_redis_connection,
    init_mongodb, init_redis, create_tables
)
from app.core.logging import (
    configure_logging, get_logger
)
from app.core.middleware.http import add_logging_middleware
from app.core.middleware.database import setup_db_logging
from app.core.middleware.mongodb import setup_mongodb_logging
from app.modules.user.routes import router as user_router
from app.modules.auth.routes import router as auth_router
from app.modules.diary.routes import router as diary_router
from app.modules.activity_state.routes import router as activity_state_router
from app.modules.recommendations_diary.routes import router as recommendations_diary_router

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Добавляем middleware для логирования HTTP запросов
add_logging_middleware(
    app,
    log_all_requests=settings.DEBUG,
    log_request_body=True,
    log_response_body=True,
    exclude_paths=["/healthcheck", "/health", "/metrics", "/docs", "/openapi.json"],
    exclude_extensions=[".js", ".css", ".ico", ".png", ".jpg"],
    max_body_length=10000,
    slow_request_threshold=1.0,
    request_id_header="X-Request-ID"
)

# Подключаем маршруты
app.include_router(auth_router, prefix="/api")
app.include_router(user_router, prefix="/api")
app.include_router(diary_router, prefix="/api")
app.include_router(activity_state_router, prefix="/api")
app.include_router(recommendations_diary_router, prefix="/api")


@app.on_event("startup")
async def startup():
    """
    Инициализация приложения при запуске
    """
    # Настраиваем систему логирования
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    json_logs = os.environ.get("LOG_FORMAT", "json").lower() == "json"
    
    configure_logging(
        log_level=log_level,
        json_format=json_logs,
        log_file=os.environ.get("LOG_FILE"),
        console_output=True,
        additional_fields={
            "app_name": settings.APP_NAME,
            "app_version": settings.APP_VERSION,
            "environment": "development" if settings.DEBUG else "production"
        }
    )
    
    # Middleware для логирования HTTP запросов уже добавлен при инициализации приложения
    
    # Получаем логгер для этого модуля
    logger = get_logger(__name__)
    
    # Инициализируем базы данных
    from app.core.database.startup import initialize_database
    from app.mongodb.mood_thought_repository import init_mood_thought_collections
    from app.mongodb.activity_state_repository import init_activity_state_collections
    from app.mongodb.recommendations_diary_repository import init_recommendations_diary_collections
    
    # Настраиваем middleware для логирования операций с базами данных
    from sqlalchemy.ext.asyncio import create_async_engine
    
    # Логирование PostgreSQL
    postgres_engine = create_async_engine(str(settings.postgres.DATABASE_URL))
    db_logger = setup_db_logging(
        engine=postgres_engine,
        slow_query_threshold=1.0,
        log_level="DEBUG" if settings.DEBUG else "INFO"
    )
    
    # Логирование MongoDB
    # Временно отключаем логирование MongoDB, так как есть проблема с доступом к приватным атрибутам
    # from motor.motor_asyncio import AsyncIOMotorClient
    # mongodb_client = AsyncIOMotorClient(settings.mongodb.MONGODB_URL)
    # mongodb_logger = setup_mongodb_logging(
    #     client=mongodb_client,
    #     slow_query_threshold=1.0,
    #     log_level="DEBUG" if settings.DEBUG else "INFO"
    # )
    
    try:
        # Инициализация баз данных
        logger.info("Initializing PostgreSQL database...")
        try:
            await initialize_database()  # SQLAlchemy/PostgreSQL + начальные данные
        except Exception as e:
            logger.warning(f"PostgreSQL initialization failed, but continuing: {e}")
        
        try:
            logger.info("Initializing MongoDB...")
            await init_mongodb()  # MongoDB
            # Попытка инициализации коллекций
            try:
                await init_mood_thought_collections()  # Инициализация коллекций для дневников
                await init_activity_state_collections()  # Инициализация коллекций для активностей и состояний
                await init_recommendations_diary_collections()  # Инициализация коллекций для рекомендаций и интегративного дневника
            except Exception as e:
                logger.warning(f"MongoDB collections initialization failed: {e}")
        except Exception as e:
            logger.warning(f"MongoDB initialization failed, but continuing without it: {e}")
        
        try:
            logger.info("Initializing Redis...")
            await init_redis()  # Redis
        except Exception as e:
            logger.warning(f"Redis initialization failed, but continuing without it: {e}")
            
        logger.info("Application startup completed successfully")
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        # Приложение все равно запустится, но с ограниченной функциональностью


@app.on_event("shutdown")
async def shutdown():
    """
    Закрытие соединений при остановке приложения
    """
    from app.core.database.mongodb import close_mongodb_connection
    from app.core.database.redis_client import close_redis_connection
    
    await close_mongodb_connection()
    await close_redis_connection()


@app.get("/")
async def read_root():
    """
    Корневой эндпоинт для проверки работы API
    """
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs_url": "/docs"
    }


@app.get("/healthcheck")
async def healthcheck():
    """
    Проверка работоспособности сервера
    """
    return {"status": "ok"}


@app.get("/api/status")
async def check_status():
    """
    Проверка статуса всех компонентов системы
    """
    pg_success, pg_message = await check_postgres_connection()
    mongo_success, mongo_message = await check_mongodb_connection()
    redis_success, redis_message = await check_redis_connection()
    
    return {
        "postgresql": {"success": pg_success, "message": pg_message},
        "mongodb": {"success": mongo_success, "message": mongo_message},
        "redis": {"success": redis_success, "message": redis_message},
    }


@app.get("/api/check-tables")
async def check_tables(db: AsyncSession = Depends(get_db)):
    """
    Проверка таблиц в базе данных PostgreSQL
    """
    try:
        # Пробуем получить список таблиц
        try:
            # Для PostgreSQL
            result = await db.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
            tables = [row[0] for row in result]
        except Exception:
            # Для SQLite
            result = await db.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in result]
            
        return {"success": True, "tables": tables}
    except Exception as e:
        error_details = traceback.format_exc()
        return {
            "success": False, 
            "error": str(e),
            "details": error_details
        }