"""
API маршруты для работы с дневниками настроения и мыслей.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from typing import List, Optional
from datetime import datetime
import logging

from app.core.auth import get_current_user
from app.models import User
from app.mongodb.mood_thought_repository import (
    create_mood_entry, get_mood_entry, get_user_mood_entries, update_mood_entry, delete_mood_entry,
    create_thought_entry, get_thought_entry, get_user_thought_entries, update_thought_entry, delete_thought_entry,
    get_mood_statistics, get_thought_statistics, get_user_mood_trends
)
from app.mongodb.mood_thought_schemas_pydantic import (
    MoodEntryCreate, MoodEntryUpdate, MoodEntryResponse,
    ThoughtEntryCreate, ThoughtEntryUpdate, ThoughtEntryResponse,
    DateRangeQuery, PaginationQuery, StatisticsPeriodQuery, TrendQuery,
    MoodStatistics, ThoughtStatistics, MoodTrend
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/diary", tags=["diary"])


# Маршруты для записей настроения

@router.post("/mood", response_model=MoodEntryResponse, status_code=201)
async def create_new_mood_entry(
    entry: MoodEntryCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Создает новую запись настроения для текущего пользователя.
    """
    # Проверяем, что пользователь создает запись для себя
    if entry.user_id != str(current_user.id):
        raise HTTPException(
            status_code=403,
            detail="Вы можете создавать записи только для своего аккаунта"
        )
    
    try:
        entry_id = await create_mood_entry(
            user_id=entry.user_id,
            mood_score=entry.mood_score,
            emotions=entry.emotions.dict() if hasattr(entry.emotions, "dict") else entry.emotions,
            timestamp=entry.timestamp,
            triggers=entry.triggers,
            physical_sensations=entry.physical_sensations,
            body_areas=entry.body_areas,
            context=entry.context,
            notes=entry.notes
        )
        
        # Получаем созданную запись
        created_entry = await get_mood_entry(entry_id)
        if not created_entry:
            raise HTTPException(
                status_code=500,
                detail="Ошибка при создании записи настроения"
            )
        
        return MoodEntryResponse.from_mongo(created_entry)
    
    except Exception as e:
        logger.error(f"Ошибка при создании записи настроения: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при создании записи настроения: {str(e)}"
        )


@router.get("/mood/{entry_id}", response_model=MoodEntryResponse)
async def get_single_mood_entry(
    entry_id: str = Path(..., title="ID записи настроения"),
    current_user: User = Depends(get_current_user)
):
    """
    Получает одну запись настроения по ID.
    """
    entry = await get_mood_entry(entry_id)
    
    if not entry:
        raise HTTPException(
            status_code=404,
            detail="Запись настроения не найдена"
        )
    
    # Проверяем доступ пользователя
    if entry["user_id"] != str(current_user.id):
        raise HTTPException(
            status_code=403,
            detail="У вас нет доступа к этой записи"
        )
    
    return MoodEntryResponse.from_mongo(entry)


@router.get("/mood", response_model=List[MoodEntryResponse])
async def get_mood_entries(
    date_range: DateRangeQuery = Depends(),
    pagination: PaginationQuery = Depends(),
    current_user: User = Depends(get_current_user)
):
    """
    Получает список записей настроения пользователя с возможностью фильтрации по датам.
    """
    sort_order = -1 if pagination.sort_desc else 1
    
    entries = await get_user_mood_entries(
        user_id=str(current_user.id),
        start_date=date_range.start_date,
        end_date=date_range.end_date,
        limit=pagination.limit,
        skip=pagination.skip,
        sort_order=sort_order
    )
    
    return [MoodEntryResponse.from_mongo(entry) for entry in entries]


@router.put("/mood/{entry_id}", response_model=MoodEntryResponse)
async def update_existing_mood_entry(
    entry_update: MoodEntryUpdate,
    entry_id: str = Path(..., title="ID записи настроения"),
    current_user: User = Depends(get_current_user)
):
    """
    Обновляет существующую запись настроения.
    """
    # Проверяем существование записи
    entry = await get_mood_entry(entry_id)
    
    if not entry:
        raise HTTPException(
            status_code=404,
            detail="Запись настроения не найдена"
        )
    
    # Проверяем доступ пользователя
    if entry["user_id"] != str(current_user.id):
        raise HTTPException(
            status_code=403,
            detail="У вас нет доступа к этой записи"
        )
    
    # Преобразуем модель в словарь и удаляем None значения
    update_data = entry_update.dict(exclude_unset=True)
    
    # Преобразуем вложенные Pydantic модели в словари
    if "emotions" in update_data and update_data["emotions"]:
        update_data["emotions"] = [emotion.dict() for emotion in update_data["emotions"]]
    
    if not update_data:
        # Если нет данных для обновления, просто возвращаем существующую запись
        return MoodEntryResponse.from_mongo(entry)
    
    # Обновляем запись
    success = await update_mood_entry(entry_id, update_data)
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Ошибка при обновлении записи настроения"
        )
    
    # Получаем обновленную запись
    updated_entry = await get_mood_entry(entry_id)
    
    return MoodEntryResponse.from_mongo(updated_entry)


@router.delete("/mood/{entry_id}", status_code=204)
async def delete_existing_mood_entry(
    entry_id: str = Path(..., title="ID записи настроения"),
    current_user: User = Depends(get_current_user)
):
    """
    Удаляет запись настроения.
    """
    # Проверяем существование записи
    entry = await get_mood_entry(entry_id)
    
    if not entry:
        raise HTTPException(
            status_code=404,
            detail="Запись настроения не найдена"
        )
    
    # Проверяем доступ пользователя
    if entry["user_id"] != str(current_user.id):
        raise HTTPException(
            status_code=403,
            detail="У вас нет доступа к этой записи"
        )
    
    # Удаляем запись
    success = await delete_mood_entry(entry_id)
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Ошибка при удалении записи настроения"
        )


@router.get("/mood/statistics", response_model=MoodStatistics)
async def get_mood_stats(
    stats_query: StatisticsPeriodQuery = Depends(),
    current_user: User = Depends(get_current_user)
):
    """
    Получает статистику настроения пользователя за указанный период.
    """
    statistics = await get_mood_statistics(
        user_id=str(current_user.id),
        period=stats_query.period,
        end_date=stats_query.end_date
    )
    
    return statistics


@router.get("/mood/trends", response_model=List[MoodTrend])
async def get_mood_trend_data(
    trend_query: TrendQuery = Depends(),
    current_user: User = Depends(get_current_user)
):
    """
    Получает данные о трендах настроения пользователя с агрегацией по интервалам.
    """
    trends = await get_user_mood_trends(
        user_id=str(current_user.id),
        interval=trend_query.interval,
        start_date=trend_query.start_date,
        end_date=trend_query.end_date,
        limit=trend_query.limit
    )
    
    return trends


# Маршруты для записей мыслей

@router.post("/thought", response_model=ThoughtEntryResponse, status_code=201)
async def create_new_thought_entry(
    entry: ThoughtEntryCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Создает новую запись мыслей для текущего пользователя.
    """
    # Проверяем, что пользователь создает запись для себя
    if entry.user_id != str(current_user.id):
        raise HTTPException(
            status_code=403,
            detail="Вы можете создавать записи только для своего аккаунта"
        )
    
    try:
        # Преобразуем Pydantic модели в словари
        automatic_thoughts = [thought.dict() for thought in entry.automatic_thoughts]
        emotions = [emotion.dict() for emotion in entry.emotions]
        
        entry_id = await create_thought_entry(
            user_id=entry.user_id,
            situation=entry.situation,
            automatic_thoughts=automatic_thoughts,
            emotions=emotions,
            timestamp=entry.timestamp,
            evidence_for=entry.evidence_for,
            evidence_against=entry.evidence_against,
            balanced_thought=entry.balanced_thought,
            new_belief_level=entry.new_belief_level,
            action_plan=entry.action_plan
        )
        
        # Получаем созданную запись
        created_entry = await get_thought_entry(entry_id)
        if not created_entry:
            raise HTTPException(
                status_code=500,
                detail="Ошибка при создании записи мыслей"
            )
        
        return ThoughtEntryResponse.from_mongo(created_entry)
    
    except Exception as e:
        logger.error(f"Ошибка при создании записи мыслей: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при создании записи мыслей: {str(e)}"
        )


@router.get("/thought/{entry_id}", response_model=ThoughtEntryResponse)
async def get_single_thought_entry(
    entry_id: str = Path(..., title="ID записи мыслей"),
    current_user: User = Depends(get_current_user)
):
    """
    Получает одну запись мыслей по ID.
    """
    entry = await get_thought_entry(entry_id)
    
    if not entry:
        raise HTTPException(
            status_code=404,
            detail="Запись мыслей не найдена"
        )
    
    # Проверяем доступ пользователя
    if entry["user_id"] != str(current_user.id):
        raise HTTPException(
            status_code=403,
            detail="У вас нет доступа к этой записи"
        )
    
    return ThoughtEntryResponse.from_mongo(entry)


@router.get("/thought", response_model=List[ThoughtEntryResponse])
async def get_thought_entries(
    date_range: DateRangeQuery = Depends(),
    pagination: PaginationQuery = Depends(),
    current_user: User = Depends(get_current_user)
):
    """
    Получает список записей мыслей пользователя с возможностью фильтрации по датам.
    """
    sort_order = -1 if pagination.sort_desc else 1
    
    entries = await get_user_thought_entries(
        user_id=str(current_user.id),
        start_date=date_range.start_date,
        end_date=date_range.end_date,
        limit=pagination.limit,
        skip=pagination.skip,
        sort_order=sort_order
    )
    
    return [ThoughtEntryResponse.from_mongo(entry) for entry in entries]


@router.put("/thought/{entry_id}", response_model=ThoughtEntryResponse)
async def update_existing_thought_entry(
    entry_update: ThoughtEntryUpdate,
    entry_id: str = Path(..., title="ID записи мыслей"),
    current_user: User = Depends(get_current_user)
):
    """
    Обновляет существующую запись мыслей.
    """
    # Проверяем существование записи
    entry = await get_thought_entry(entry_id)
    
    if not entry:
        raise HTTPException(
            status_code=404,
            detail="Запись мыслей не найдена"
        )
    
    # Проверяем доступ пользователя
    if entry["user_id"] != str(current_user.id):
        raise HTTPException(
            status_code=403,
            detail="У вас нет доступа к этой записи"
        )
    
    # Преобразуем модель в словарь и удаляем None значения
    update_data = entry_update.dict(exclude_unset=True)
    
    # Преобразуем вложенные Pydantic модели в словари
    if "automatic_thoughts" in update_data and update_data["automatic_thoughts"]:
        update_data["automatic_thoughts"] = [thought.dict() for thought in update_data["automatic_thoughts"]]
    
    if "emotions" in update_data and update_data["emotions"]:
        update_data["emotions"] = [emotion.dict() for emotion in update_data["emotions"]]
    
    if not update_data:
        # Если нет данных для обновления, просто возвращаем существующую запись
        return ThoughtEntryResponse.from_mongo(entry)
    
    # Обновляем запись
    success = await update_thought_entry(entry_id, update_data)
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Ошибка при обновлении записи мыслей"
        )
    
    # Получаем обновленную запись
    updated_entry = await get_thought_entry(entry_id)
    
    return ThoughtEntryResponse.from_mongo(updated_entry)


@router.delete("/thought/{entry_id}", status_code=204)
async def delete_existing_thought_entry(
    entry_id: str = Path(..., title="ID записи мыслей"),
    current_user: User = Depends(get_current_user)
):
    """
    Удаляет запись мыслей.
    """
    # Проверяем существование записи
    entry = await get_thought_entry(entry_id)
    
    if not entry:
        raise HTTPException(
            status_code=404,
            detail="Запись мыслей не найдена"
        )
    
    # Проверяем доступ пользователя
    if entry["user_id"] != str(current_user.id):
        raise HTTPException(
            status_code=403,
            detail="У вас нет доступа к этой записи"
        )
    
    # Удаляем запись
    success = await delete_thought_entry(entry_id)
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Ошибка при удалении записи мыслей"
        )


@router.get("/thought/statistics", response_model=ThoughtStatistics)
async def get_thought_stats(
    stats_query: StatisticsPeriodQuery = Depends(),
    current_user: User = Depends(get_current_user)
):
    """
    Получает статистику мыслей пользователя за указанный период.
    """
    statistics = await get_thought_statistics(
        user_id=str(current_user.id),
        period=stats_query.period,
        end_date=stats_query.end_date
    )
    
    return statistics