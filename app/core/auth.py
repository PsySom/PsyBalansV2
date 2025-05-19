from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.user import schemas, service
from app.models.user import User
from app.core.security import SECRET_KEY, ALGORITHM

# Схема OAuth2 для получения токена из запроса
# URL должен быть указан относительно root (без префикса /api, который добавляется в main.py)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    """
    Аутентификация пользователя по email и паролю
    :return: Объект пользователя или None, если аутентификация не удалась
    """
    user = await service.get_user_by_email(db, email)
    if not user:
        return None
    
    from app.core.security import verify_password
    if not verify_password(password, user.hashed_password):
        return None
    
    return user

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Получение текущего пользователя по токену
    :raises: HTTPException с кодом 401, если токен недействителен
    :return: Объект пользователя
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Декодирование JWT токена
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if user_id is None or token_type != "access":
            raise credentials_exception
            
    except (JWTError, ValidationError):
        raise credentials_exception
        
    # Получение пользователя из БД
    user = await service.get_user_by_id(db, user_id)
    if user is None:
        raise credentials_exception
        
    return user

# Зависимость для получения текущего активного пользователя
async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Проверка, что пользователь активен
    :raises: HTTPException с кодом 400, если пользователь неактивен
    :return: Объект пользователя
    """
    # Проверка активности пользователя
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неактивный пользователь")
    return current_user