from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt

from app.core.database import get_db
from app.modules.user import schemas, service
from app.core import auth, security

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=schemas.Token)
async def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    OAuth2 совместимый токен логина, получение токенов для будущих запросов
    """
    # Аутентификация пользователя
    user = await auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Создание доступа и обновления токенов
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=security.REFRESH_TOKEN_EXPIRE_DAYS)
    
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )
    refresh_token = security.create_refresh_token(
        user.id, expires_delta=refresh_token_expires
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/refresh-token", response_model=schemas.Token)
async def refresh_token(
    token_data: schemas.TokenRefresh,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Получение нового access токена используя refresh токен
    """
    try:
        # Декодирование refresh токена
        payload = jwt.decode(
            token_data.refresh_token, 
            security.SECRET_KEY, 
            algorithms=[security.ALGORITHM]
        )
        token_type = payload.get("type")
        user_id = payload.get("sub")
        
        # Проверка типа токена
        if token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный тип токена",
            )
            
        # Получение пользователя
        user = await service.get_user_by_id(db, int(user_id))
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден",
            )
            
        # Создание новых токенов
        access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=security.REFRESH_TOKEN_EXPIRE_DAYS)
        
        access_token = security.create_access_token(
            user.id, expires_delta=access_token_expires
        )
        refresh_token = security.create_refresh_token(
            user.id, expires_delta=refresh_token_expires
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh токен истек",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный refresh токен",
            headers={"WWW-Authenticate": "Bearer"},
        )