from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from typing import Optional, Dict, Any, List
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv(override=True)


class PostgresSettings(BaseSettings):
    """
    Настройки PostgreSQL
    """
    POSTGRES_USER: str = Field(default="postgres")
    POSTGRES_PASSWORD: str = Field(default="")
    POSTGRES_HOST: str = Field(default="localhost")
    POSTGRES_PORT: int = Field(default=5432)  # Изменено на int
    POSTGRES_DB: str = Field(default="psybalans")
    DATABASE_URL: Optional[PostgresDsn] = None

    # В Pydantic 2.x, validator заменяется на field_validator
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info: Dict[str, Any]) -> str:
        if isinstance(v, str) and v:
            return v
        
        values = info.data
        
        port = values.get("POSTGRES_PORT")
        # Убедимся, что порт - целое число
        if isinstance(port, str):
            try:
                port = int(port)
            except ValueError:
                port = 5432
                
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=values.get("POSTGRES_USER"),
            password=values.get("POSTGRES_PASSWORD"),
            host=values.get("POSTGRES_HOST"),
            port=port,
            path=f"/{values.get('POSTGRES_DB') or ''}",
        )

    model_config = SettingsConfigDict(
        env_prefix="POSTGRES_",
        extra="ignore"
    )


class MongoDBSettings(BaseSettings):
    """
    Настройки MongoDB
    """
    MONGODB_URL: str = Field(default="mongodb://localhost:27017")
    MONGODB_DB_NAME: str = Field(default="psybalans")

    model_config = SettingsConfigDict(
        env_prefix="MONGODB_",
        extra="ignore"
    )


class RedisSettings(BaseSettings):
    """
    Настройки Redis
    """
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_DB: int = Field(default=0)
    REDIS_PASSWORD: Optional[str] = None
    REDIS_URL: Optional[RedisDsn] = None

    @field_validator("REDIS_URL", mode="before")
    @classmethod
    def assemble_redis_connection(cls, v: Optional[str], info: Dict[str, Any]) -> str:
        if isinstance(v, str) and v:
            return v
        
        values = info.data
        
        port = values.get("REDIS_PORT")
        # Убедимся, что порт - целое число
        if isinstance(port, str):
            try:
                port = int(port)
            except ValueError:
                port = 6379
        
        password_part = ""
        if values.get("REDIS_PASSWORD"):
            password_part = f":{values.get('REDIS_PASSWORD')}@"
            
        return f"redis://{password_part}{values.get('REDIS_HOST')}:{port}/{values.get('REDIS_DB')}"

    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        extra="ignore"
    )


class SecuritySettings(BaseSettings):
    """
    Настройки безопасности
    """
    SECRET_KEY: str = Field(default="your-secret-key-here")
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)

    model_config = SettingsConfigDict(
        env_prefix="SECURITY_",
        extra="ignore"
    )


class RetrySettings(BaseSettings):
    """
    Настройки механизма повторных попыток
    """
    MAX_ATTEMPTS: int = Field(default=3)
    BASE_DELAY: float = Field(default=0.1)
    MAX_DELAY: float = Field(default=10.0)
    JITTER: float = Field(default=0.1)
    TIMEOUT: Optional[float] = Field(default=None)
    
    model_config = SettingsConfigDict(
        env_prefix="RETRY_",
        extra="ignore"
    )


class Settings(BaseSettings):
    """
    Общие настройки приложения
    """
    APP_NAME: str = Field(default="PsyBalans API")
    APP_VERSION: str = Field(default="0.1.0")
    APP_DESCRIPTION: str = Field(default="API для психологической платформы PsyBalans")
    DEBUG: bool = Field(default=False)
    
    # Прямые настройки для соединений
    DATABASE_URL: Optional[str] = Field(default=None)
    SECRET_KEY: str = Field(default="your-secret-key-here")
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)
    
    # Вложенные настройки для различных компонентов
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    mongodb: MongoDBSettings = Field(default_factory=MongoDBSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    retry: RetrySettings = Field(default_factory=RetrySettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


# Создаем экземпляр настроек
settings = Settings()