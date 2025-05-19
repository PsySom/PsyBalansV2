from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.security import get_password_hash
from app.modules.user import schemas
from app.models.user import User
import uuid

async def get_user_by_email(db: AsyncSession, email: str):
    """Получение пользователя по email"""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()

async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID):
    """Получение пользователя по ID"""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, user: schemas.UserCreate):
    """Создание нового пользователя"""
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        hashed_password=hashed_password,
        first_name=user.first_name,
        last_name=user.last_name,
        is_active=True,
        is_superuser=False
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def update_user(db: AsyncSession, user_id: uuid.UUID, user_data: schemas.UserUpdate):
    """Обновление данных пользователя"""
    db_user = await get_user_by_id(db, user_id)
    if not db_user:
        return None
        
    user_data_dict = user_data.model_dump(exclude_unset=True)
    
    # Если обновляется пароль, хешируем его
    if "password" in user_data_dict:
        user_data_dict["hashed_password"] = get_password_hash(user_data_dict["password"])
        del user_data_dict["password"]
    
    # Обновляем атрибуты пользователя
    for key, value in user_data_dict.items():
        setattr(db_user, key, value)
    
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100):
    """Получение списка пользователей с пагинацией"""
    result = await db.execute(select(User).offset(skip).limit(limit))
    return result.scalars().all()

async def delete_user(db: AsyncSession, user_id: uuid.UUID):
    """Удаление пользователя"""
    db_user = await get_user_by_id(db, user_id)
    if not db_user:
        return False
    
    await db.delete(db_user)
    await db.commit()
    return True

async def deactivate_user(db: AsyncSession, user_id: uuid.UUID):
    """Деактивация пользователя"""
    db_user = await get_user_by_id(db, user_id)
    if not db_user:
        return None
    
    db_user.is_active = False
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def activate_user(db: AsyncSession, user_id: uuid.UUID):
    """Активация пользователя"""
    db_user = await get_user_by_id(db, user_id)
    if not db_user:
        return None
    
    db_user.is_active = True
    await db.commit()
    await db.refresh(db_user)
    return db_user