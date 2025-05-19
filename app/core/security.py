from datetime import datetime, timedelta
import os
from typing import Any, Optional

from jose import jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

# Загрузка настроек из .env
load_dotenv()

# Константы конфигурации JWT из переменных окружения или дефолтные значения
SECRET_KEY = os.getenv("SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Контекст для хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка соответствия пароля хешу"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Получение хеша пароля"""
    return pwd_context.hash(password)

def create_access_token(subject: Any, expires_delta: Optional[timedelta] = None) -> str:
    """
    Создание JWT access токена
    :param subject: Идентификатор пользователя (обычно user_id)
    :param expires_delta: Время жизни токена
    :return: Строка JWT токена
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(subject: Any, expires_delta: Optional[timedelta] = None) -> str:
    """
    Создание JWT refresh токена
    :param subject: Идентификатор пользователя (обычно user_id)
    :param expires_delta: Время жизни токена
    :return: Строка JWT токена
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt