from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime

class UserCreate(BaseModel):
    """Схема для создания пользователя"""
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class UserUpdate(BaseModel):
    """Схема для обновления пользователя"""
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class UserOut(BaseModel):
    """Схема для вывода пользователя"""
    id: UUID
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = {
        "from_attributes": True
    }

class UserInDB(UserOut):
    """Схема пользователя с хешем пароля (для внутреннего использования)"""
    hashed_password: str

class Token(BaseModel):
    """Схема для токена аутентификации"""
    access_token: str
    refresh_token: str
    token_type: str

class TokenPayload(BaseModel):
    """Схема полезной нагрузки токена"""
    sub: Optional[str] = None
    exp: Optional[int] = None
    type: Optional[str] = None

class TokenRefresh(BaseModel):
    """Схема для обновления токена"""
    refresh_token: str