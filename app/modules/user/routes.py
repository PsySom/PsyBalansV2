from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from app.modules.user import schemas, service
from app.models.user import User
from app.core.database import get_db
from app.core.auth import get_current_active_user, get_current_user

router = APIRouter(prefix="/user", tags=["user"])

@router.post("/register", response_model=schemas.UserOut)
async def register(
    user: schemas.UserCreate, 
    db: AsyncSession = Depends(get_db)
):
    """Регистрация нового пользователя"""
    existing_user = await service.get_user_by_email(db, user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует"
        )
    return await service.create_user(db, user)

@router.get("/me", response_model=schemas.UserOut)
async def read_user_me(
    current_user: User = Depends(get_current_active_user)
):
    """Получение информации о текущем пользователе"""
    return current_user

@router.put("/me", response_model=schemas.UserOut)
async def update_user_me(
    user_update: schemas.UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Обновление информации о текущем пользователе"""
    # Проверка на уникальность email при его обновлении
    if user_update.email and user_update.email != current_user.email:
        existing_user = await service.get_user_by_email(db, user_update.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким email уже существует"
            )
    
    updated_user = await service.update_user(db, current_user.id, user_update)
    return updated_user

@router.get("/test")
async def test_user_route():
    """Тестовый маршрут"""
    return {"message": "User API works"}

# Административные маршруты (требуют прав суперпользователя)

@router.get("/admin/users", response_model=List[schemas.UserOut])
async def get_users(
    skip: int = 0, 
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение списка пользователей (только для администраторов)
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    return await service.get_users(db, skip=skip, limit=limit)

@router.get("/admin/users/{user_id}", response_model=schemas.UserOut)
async def get_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение пользователя по ID (только для администраторов)
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    
    user = await service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    return user

@router.put("/admin/users/{user_id}/activate", response_model=schemas.UserOut)
async def activate_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Активация пользователя (только для администраторов)
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    
    user = await service.activate_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    return user

@router.put("/admin/users/{user_id}/deactivate", response_model=schemas.UserOut)
async def deactivate_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Деактивация пользователя (только для администраторов)
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    
    user = await service.deactivate_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    return user

@router.delete("/admin/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Удаление пользователя (только для администраторов)
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )
    
    # Не позволяем удалить самого себя
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Невозможно удалить свою учетную запись"
        )
    
    success = await service.delete_user(db, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    return None