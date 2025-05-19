"""
API маршруты для работы с рекомендациями и интегративным дневником.
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Path, status
from datetime import datetime, timedelta

from app.core.auth import get_current_active_user
from app.models.user import User
from app.mongodb.recommendations_diary_schemas_pydantic import (
    RecommendationCreate, RecommendationUpdate, Recommendation,
    DiaryEntryCreate, DiaryEntryUpdate, DiaryEntry,
    ConversationMessageBase
)
from app.mongodb.recommendations_diary_repository import (
    RecommendationRepository, DiaryEntriesRepository
)

# Создаем экземпляры репозиториев
recommendation_repository = RecommendationRepository()
diary_entries_repository = DiaryEntriesRepository()

router = APIRouter(
    prefix="/api/recommendations-diary",
    tags=["Recommendations & Diary"]
)


# Маршруты для рекомендаций
@router.post("/recommendations", response_model=Dict[str, str], status_code=status.HTTP_201_CREATED)
async def create_recommendation(
    recommendation: RecommendationCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Создание новой рекомендации системы.
    """
    recommendation_id = await recommendation_repository.create_recommendation(recommendation)
    return {"id": recommendation_id}


@router.get("/recommendations/{recommendation_id}", response_model=Dict[str, Any])
async def get_recommendation(
    recommendation_id: str = Path(..., description="ID рекомендации"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получение рекомендации по ID.
    """
    recommendation = await recommendation_repository.get_recommendation(recommendation_id)
    if not recommendation:
        raise HTTPException(status_code=404, detail="Рекомендация не найдена")
    return recommendation


@router.put("/recommendations/{recommendation_id}", response_model=Dict[str, Any])
async def update_recommendation(
    update_data: RecommendationUpdate,
    recommendation_id: str = Path(..., description="ID рекомендации"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновление рекомендации по ID.
    """
    updated_recommendation = await recommendation_repository.update_recommendation(
        recommendation_id, update_data
    )
    if not updated_recommendation:
        raise HTTPException(status_code=404, detail="Рекомендация не найдена")
    return updated_recommendation


@router.delete("/recommendations/{recommendation_id}", response_model=Dict[str, bool])
async def delete_recommendation(
    recommendation_id: str = Path(..., description="ID рекомендации"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Удаление рекомендации по ID.
    """
    success = await recommendation_repository.delete_recommendation(recommendation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Рекомендация не найдена")
    return {"success": True}


@router.get("/recommendations/user/{user_id}", response_model=List[Dict[str, Any]])
async def get_user_recommendations(
    user_id: str = Path(..., description="ID пользователя"),
    limit: int = Query(10, ge=1, le=100, description="Количество результатов"),
    skip: int = Query(0, ge=0, description="Смещение результатов"),
    start_date: Optional[datetime] = Query(None, description="Начальная дата (ISO формат)"),
    end_date: Optional[datetime] = Query(None, description="Конечная дата (ISO формат)"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получение рекомендаций пользователя.
    """
    recommendations = await recommendation_repository.get_user_recommendations(
        user_id, limit, skip, start_date, end_date
    )
    return recommendations


@router.get("/recommendations/type/{recommendation_type}", response_model=List[Dict[str, Any]])
async def get_recommendations_by_type(
    recommendation_type: str = Path(..., description="Тип рекомендации"),
    limit: int = Query(10, ge=1, le=100, description="Количество результатов"),
    skip: int = Query(0, ge=0, description="Смещение результатов"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получение рекомендаций по типу.
    """
    recommendations = await recommendation_repository.get_recommendations_by_type(
        recommendation_type, limit, skip
    )
    return recommendations


@router.get("/recommendations/trigger/{trigger_type}", response_model=List[Dict[str, Any]])
async def get_recommendations_by_trigger(
    trigger_type: str = Path(..., description="Тип триггера"),
    limit: int = Query(10, ge=1, le=100, description="Количество результатов"),
    skip: int = Query(0, ge=0, description="Смещение результатов"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получение рекомендаций по типу триггера.
    """
    recommendations = await recommendation_repository.get_recommendations_by_trigger(
        trigger_type, limit, skip
    )
    return recommendations


@router.get("/recommendations/response/{status}", response_model=List[Dict[str, Any]])
async def get_recommendations_by_response(
    status: str = Path(..., description="Статус ответа пользователя"),
    limit: int = Query(10, ge=1, le=100, description="Количество результатов"),
    skip: int = Query(0, ge=0, description="Смещение результатов"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получение рекомендаций по статусу ответа пользователя.
    """
    recommendations = await recommendation_repository.get_recommendations_by_response_status(
        status, limit, skip
    )
    return recommendations


@router.get("/recommendations/stats", response_model=Dict[str, Any])
async def get_recommendations_stats(
    user_id: Optional[str] = Query(None, description="ID пользователя (опционально)"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получение статистики по рекомендациям.
    """
    stats = await recommendation_repository.get_recommendations_stats(user_id)
    return stats


# Маршруты для интегративного дневника
@router.post("/diary", response_model=Dict[str, str], status_code=status.HTTP_201_CREATED)
async def create_diary_entry(
    entry: DiaryEntryCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Создание новой записи в интегративном дневнике.
    """
    entry_id = await diary_entries_repository.create_diary_entry(entry)
    return {"id": entry_id}


@router.get("/diary/{entry_id}", response_model=Dict[str, Any])
async def get_diary_entry(
    entry_id: str = Path(..., description="ID записи дневника"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получение записи дневника по ID.
    """
    entry = await diary_entries_repository.get_diary_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Запись дневника не найдена")
    return entry


@router.put("/diary/{entry_id}", response_model=Dict[str, Any])
async def update_diary_entry(
    update_data: DiaryEntryUpdate,
    entry_id: str = Path(..., description="ID записи дневника"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновление записи дневника по ID.
    """
    updated_entry = await diary_entries_repository.update_diary_entry(
        entry_id, update_data
    )
    if not updated_entry:
        raise HTTPException(status_code=404, detail="Запись дневника не найдена")
    return updated_entry


@router.delete("/diary/{entry_id}", response_model=Dict[str, bool])
async def delete_diary_entry(
    entry_id: str = Path(..., description="ID записи дневника"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Удаление записи дневника по ID.
    """
    success = await diary_entries_repository.delete_diary_entry(entry_id)
    if not success:
        raise HTTPException(status_code=404, detail="Запись дневника не найдена")
    return {"success": True}


@router.get("/diary/user/{user_id}", response_model=List[Dict[str, Any]])
async def get_user_diary_entries(
    user_id: str = Path(..., description="ID пользователя"),
    limit: int = Query(10, ge=1, le=100, description="Количество результатов"),
    skip: int = Query(0, ge=0, description="Смещение результатов"),
    start_date: Optional[datetime] = Query(None, description="Начальная дата (ISO формат)"),
    end_date: Optional[datetime] = Query(None, description="Конечная дата (ISO формат)"),
    entry_type: Optional[str] = Query(None, description="Тип записи"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получение записей дневника пользователя.
    """
    entries = await diary_entries_repository.get_user_diary_entries(
        user_id, limit, skip, start_date, end_date, entry_type
    )
    return entries


@router.get("/diary/session/{session_id}", response_model=List[Dict[str, Any]])
async def get_entries_by_session(
    session_id: str = Path(..., description="ID сессии"),
    limit: int = Query(10, ge=1, le=100, description="Количество результатов"),
    skip: int = Query(0, ge=0, description="Смещение результатов"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получение записей дневника по ID сессии.
    """
    entries = await diary_entries_repository.get_entries_by_session(
        session_id, limit, skip
    )
    return entries


@router.get("/diary/type/{entry_type}", response_model=List[Dict[str, Any]])
async def get_entries_by_type(
    entry_type: str = Path(..., description="Тип записи"),
    limit: int = Query(10, ge=1, le=100, description="Количество результатов"),
    skip: int = Query(0, ge=0, description="Смещение результатов"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получение записей дневника по типу.
    """
    entries = await diary_entries_repository.get_entries_by_type(
        entry_type, limit, skip
    )
    return entries


@router.get("/diary/mood-range", response_model=List[Dict[str, Any]])
async def get_entries_by_mood_range(
    min_mood: float = Query(..., ge=-10.0, le=10.0, description="Минимальное настроение"),
    max_mood: float = Query(..., ge=-10.0, le=10.0, description="Максимальное настроение"),
    limit: int = Query(10, ge=1, le=100, description="Количество результатов"),
    skip: int = Query(0, ge=0, description="Смещение результатов"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получение записей дневника по диапазону настроения.
    """
    entries = await DiaryEntriesRepository.get_entries_by_mood_range(
        min_mood, max_mood, limit, skip
    )
    return entries


@router.get("/diary/linked/{entry_id}", response_model=List[Dict[str, Any]])
async def get_linked_entries(
    entry_id: str = Path(..., description="ID записи дневника"),
    limit: int = Query(10, ge=1, le=100, description="Количество результатов"),
    skip: int = Query(0, ge=0, description="Смещение результатов"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получение записей дневника, связанных с указанной записью.
    """
    entries = await DiaryEntriesRepository.get_linked_entries(
        entry_id, limit, skip
    )
    return entries


@router.post("/diary/{entry_id}/message", response_model=Dict[str, Any])
async def add_message_to_conversation(
    entry_id: str = Path(..., description="ID записи дневника"),
    role: str = Query(..., description="Роль в диалоге (system/user)"),
    content: str = Query(..., description="Содержание сообщения"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Добавление нового сообщения в диалог записи дневника.
    """
    updated_entry = await diary_entries_repository.add_message_to_conversation(
        entry_id, role, content
    )
    if not updated_entry:
        raise HTTPException(status_code=404, detail="Запись дневника не найдена")
    return updated_entry


@router.put("/diary/{entry_id}/extracted-data", response_model=Dict[str, Any])
async def update_extracted_data(
    entry_id: str = Path(..., description="ID записи дневника"),
    extracted_data: Dict[str, Any] = None,
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновление извлеченных данных в записи дневника.
    """
    updated_entry = await diary_entries_repository.update_extracted_data(
        entry_id, extracted_data
    )
    if not updated_entry:
        raise HTTPException(status_code=404, detail="Запись дневника не найдена")
    return updated_entry


@router.post("/diary/{entry_id}/link", response_model=Dict[str, Any])
async def add_linked_entry(
    entry_id: str = Path(..., description="ID записи дневника"),
    linked_entry_type: str = Query(..., description="Тип связанной записи"),
    linked_entry_id: str = Query(..., description="ID связанной записи"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Добавление связанной записи к записи дневника.
    """
    updated_entry = await diary_entries_repository.add_linked_entry(
        entry_id, linked_entry_type, linked_entry_id
    )
    if not updated_entry:
        raise HTTPException(status_code=404, detail="Запись дневника не найдена или связываемая запись не найдена")
    return updated_entry


@router.get("/diary/stats", response_model=Dict[str, Any])
async def get_diary_stats(
    user_id: Optional[str] = Query(None, description="ID пользователя (опционально)"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Получение статистики по дневниковым записям.
    """
    stats = await diary_entries_repository.get_diary_stats(user_id)
    return stats