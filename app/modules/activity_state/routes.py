"""
API маршруты для работы с оценками активностей и снимками состояния пользователя.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from app.core.auth import get_current_user
from app.models import User
from app.mongodb.activity_state_repository import (
    # Функции для работы с оценками активностей
    create_activity_evaluation, get_activity_evaluation, get_user_activity_evaluations,
    update_activity_evaluation, delete_activity_evaluation, get_activity_impact_statistics,
    
    # Функции для работы со снимками состояния
    create_state_snapshot, get_state_snapshot, get_user_state_snapshots,
    update_state_snapshot, delete_state_snapshot, get_state_trends,
    get_needs_satisfaction_trends, get_context_factors_analysis
)
from app.mongodb.activity_state_schemas_pydantic import (
    # Модели для оценок активностей
    ActivityEvaluationCreate, ActivityEvaluationUpdate, ActivityEvaluationResponse,
    
    # Модели для снимков состояния
    StateSnapshotCreate, StateSnapshotUpdate, StateSnapshotResponse,
    
    # Модели для запросов и пагинации
    DateRangeQuery, PaginationQuery, ActivityStatisticsQuery,
    StateTrendsQuery, NeedsTrendsQuery, ContextAnalysisQuery
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/activity-state", tags=["activity-state"])


# Маршруты для оценок активностей

@router.post("/evaluations", response_model=ActivityEvaluationResponse, status_code=201)
async def create_new_activity_evaluation(
    evaluation: ActivityEvaluationCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Создает новую оценку активности для текущего пользователя.
    """
    # Проверяем, что пользователь создает запись для себя
    if evaluation.user_id != str(current_user.id):
        raise HTTPException(
            status_code=403,
            detail="Вы можете создавать оценки только для своего аккаунта"
        )
    
    try:
        # Преобразуем Pydantic модели в словари
        needs_impact = None
        if evaluation.needs_impact:
            needs_impact = [impact.dict() for impact in evaluation.needs_impact]
        
        evaluation_id = await create_activity_evaluation(
            user_id=evaluation.user_id,
            activity_id=evaluation.activity_id,
            timestamp=evaluation.timestamp,
            completion_status=evaluation.completion_status,
            schedule_id=evaluation.schedule_id,
            satisfaction_result=evaluation.satisfaction_result,
            satisfaction_process=evaluation.satisfaction_process,
            energy_impact=evaluation.energy_impact,
            stress_impact=evaluation.stress_impact,
            needs_impact=needs_impact,
            duration_minutes=evaluation.duration_minutes,
            notes=evaluation.notes
        )
        
        # Получаем созданную запись
        created_evaluation = await get_activity_evaluation(evaluation_id)
        if not created_evaluation:
            raise HTTPException(
                status_code=500,
                detail="Ошибка при создании оценки активности"
            )
        
        return ActivityEvaluationResponse.from_mongo(created_evaluation)
    
    except Exception as e:
        logger.error(f"Ошибка при создании оценки активности: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при создании оценки активности: {str(e)}"
        )


@router.get("/evaluations/{evaluation_id}", response_model=ActivityEvaluationResponse)
async def get_single_activity_evaluation(
    evaluation_id: str = Path(..., title="ID оценки активности"),
    current_user: User = Depends(get_current_user)
):
    """
    Получает одну оценку активности по ID.
    """
    evaluation = await get_activity_evaluation(evaluation_id)
    
    if not evaluation:
        raise HTTPException(
            status_code=404,
            detail="Оценка активности не найдена"
        )
    
    # Проверяем доступ пользователя
    if evaluation["user_id"] != str(current_user.id):
        raise HTTPException(
            status_code=403,
            detail="У вас нет доступа к этой оценке"
        )
    
    return ActivityEvaluationResponse.from_mongo(evaluation)


@router.get("/evaluations", response_model=List[ActivityEvaluationResponse])
async def get_activity_evaluations(
    activity_id: Optional[str] = None,
    schedule_id: Optional[str] = None,
    completion_status: Optional[str] = None,
    date_range: DateRangeQuery = Depends(),
    pagination: PaginationQuery = Depends(),
    current_user: User = Depends(get_current_user)
):
    """
    Получает список оценок активностей пользователя с возможностью фильтрации.
    """
    sort_order = -1 if pagination.sort_desc else 1
    
    evaluations = await get_user_activity_evaluations(
        user_id=str(current_user.id),
        activity_id=activity_id,
        schedule_id=schedule_id,
        start_date=date_range.start_date,
        end_date=date_range.end_date,
        completion_status=completion_status,
        limit=pagination.limit,
        skip=pagination.skip,
        sort_order=sort_order
    )
    
    return [ActivityEvaluationResponse.from_mongo(evaluation) for evaluation in evaluations]


@router.put("/evaluations/{evaluation_id}", response_model=ActivityEvaluationResponse)
async def update_existing_activity_evaluation(
    evaluation_update: ActivityEvaluationUpdate,
    evaluation_id: str = Path(..., title="ID оценки активности"),
    current_user: User = Depends(get_current_user)
):
    """
    Обновляет существующую оценку активности.
    """
    # Проверяем существование записи
    evaluation = await get_activity_evaluation(evaluation_id)
    
    if not evaluation:
        raise HTTPException(
            status_code=404,
            detail="Оценка активности не найдена"
        )
    
    # Проверяем доступ пользователя
    if evaluation["user_id"] != str(current_user.id):
        raise HTTPException(
            status_code=403,
            detail="У вас нет доступа к этой оценке"
        )
    
    # Преобразуем модель в словарь и удаляем None значения
    update_data = evaluation_update.dict(exclude_unset=True)
    
    # Преобразуем вложенные Pydantic модели в словари
    if "needs_impact" in update_data and update_data["needs_impact"]:
        update_data["needs_impact"] = [impact.dict() for impact in update_data["needs_impact"]]
    
    if not update_data:
        # Если нет данных для обновления, просто возвращаем существующую запись
        return ActivityEvaluationResponse.from_mongo(evaluation)
    
    # Обновляем запись
    success = await update_activity_evaluation(evaluation_id, update_data)
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Ошибка при обновлении оценки активности"
        )
    
    # Получаем обновленную запись
    updated_evaluation = await get_activity_evaluation(evaluation_id)
    
    return ActivityEvaluationResponse.from_mongo(updated_evaluation)


@router.delete("/evaluations/{evaluation_id}", status_code=204)
async def delete_existing_activity_evaluation(
    evaluation_id: str = Path(..., title="ID оценки активности"),
    current_user: User = Depends(get_current_user)
):
    """
    Удаляет оценку активности.
    """
    # Проверяем существование записи
    evaluation = await get_activity_evaluation(evaluation_id)
    
    if not evaluation:
        raise HTTPException(
            status_code=404,
            detail="Оценка активности не найдена"
        )
    
    # Проверяем доступ пользователя
    if evaluation["user_id"] != str(current_user.id):
        raise HTTPException(
            status_code=403,
            detail="У вас нет доступа к этой оценке"
        )
    
    # Удаляем запись
    success = await delete_activity_evaluation(evaluation_id)
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Ошибка при удалении оценки активности"
        )


@router.get("/evaluations/statistics", response_model=Dict[str, Any])
async def get_activities_statistics(
    stats_query: ActivityStatisticsQuery = Depends(),
    current_user: User = Depends(get_current_user)
):
    """
    Получает статистику влияния активностей на состояние и потребности пользователя.
    """
    try:
        statistics = await get_activity_impact_statistics(
            user_id=str(current_user.id),
            need_id=stats_query.need_id,
            period=stats_query.period,
            end_date=stats_query.end_date
        )
        
        return statistics
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка при получении статистики активностей: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении статистики: {str(e)}"
        )


# Маршруты для снимков состояния

@router.post("/snapshots", response_model=StateSnapshotResponse, status_code=201)
async def create_new_state_snapshot(
    snapshot: StateSnapshotCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Создает новый снимок состояния для текущего пользователя.
    """
    # Проверяем, что пользователь создает запись для себя
    if snapshot.user_id != str(current_user.id):
        raise HTTPException(
            status_code=403,
            detail="Вы можете создавать снимки состояния только для своего аккаунта"
        )
    
    try:
        # Преобразуем Pydantic модели в словари
        mood_data = snapshot.mood.dict()
        energy_data = snapshot.energy.dict()
        stress_data = snapshot.stress.dict()
        
        needs_data = None
        if snapshot.needs:
            needs_data = [need.dict() for need in snapshot.needs]
        
        snapshot_id = await create_state_snapshot(
            user_id=snapshot.user_id,
            timestamp=snapshot.timestamp,
            snapshot_type=snapshot.snapshot_type,
            mood=mood_data,
            energy=energy_data,
            stress=stress_data,
            needs=needs_data,
            focus_level=snapshot.focus_level,
            sleep_quality=snapshot.sleep_quality,
            context_factors=snapshot.context_factors
        )
        
        # Получаем созданную запись
        created_snapshot = await get_state_snapshot(snapshot_id)
        if not created_snapshot:
            raise HTTPException(
                status_code=500,
                detail="Ошибка при создании снимка состояния"
            )
        
        return StateSnapshotResponse.from_mongo(created_snapshot)
    
    except Exception as e:
        logger.error(f"Ошибка при создании снимка состояния: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при создании снимка состояния: {str(e)}"
        )


@router.get("/snapshots/{snapshot_id}", response_model=StateSnapshotResponse)
async def get_single_state_snapshot(
    snapshot_id: str = Path(..., title="ID снимка состояния"),
    current_user: User = Depends(get_current_user)
):
    """
    Получает один снимок состояния по ID.
    """
    snapshot = await get_state_snapshot(snapshot_id)
    
    if not snapshot:
        raise HTTPException(
            status_code=404,
            detail="Снимок состояния не найден"
        )
    
    # Проверяем доступ пользователя
    if snapshot["user_id"] != str(current_user.id):
        raise HTTPException(
            status_code=403,
            detail="У вас нет доступа к этому снимку состояния"
        )
    
    return StateSnapshotResponse.from_mongo(snapshot)


@router.get("/snapshots", response_model=List[StateSnapshotResponse])
async def get_state_snapshots(
    snapshot_type: Optional[str] = None,
    date_range: DateRangeQuery = Depends(),
    pagination: PaginationQuery = Depends(),
    current_user: User = Depends(get_current_user)
):
    """
    Получает список снимков состояния пользователя с возможностью фильтрации.
    """
    sort_order = -1 if pagination.sort_desc else 1
    
    snapshots = await get_user_state_snapshots(
        user_id=str(current_user.id),
        snapshot_type=snapshot_type,
        start_date=date_range.start_date,
        end_date=date_range.end_date,
        limit=pagination.limit,
        skip=pagination.skip,
        sort_order=sort_order
    )
    
    return [StateSnapshotResponse.from_mongo(snapshot) for snapshot in snapshots]


@router.put("/snapshots/{snapshot_id}", response_model=StateSnapshotResponse)
async def update_existing_state_snapshot(
    snapshot_update: StateSnapshotUpdate,
    snapshot_id: str = Path(..., title="ID снимка состояния"),
    current_user: User = Depends(get_current_user)
):
    """
    Обновляет существующий снимок состояния.
    """
    # Проверяем существование записи
    snapshot = await get_state_snapshot(snapshot_id)
    
    if not snapshot:
        raise HTTPException(
            status_code=404,
            detail="Снимок состояния не найден"
        )
    
    # Проверяем доступ пользователя
    if snapshot["user_id"] != str(current_user.id):
        raise HTTPException(
            status_code=403,
            detail="У вас нет доступа к этому снимку состояния"
        )
    
    # Преобразуем модель в словарь и удаляем None значения
    update_data = snapshot_update.dict(exclude_unset=True)
    
    # Преобразуем вложенные Pydantic модели в словари
    if "mood" in update_data and update_data["mood"]:
        update_data["mood"] = update_data["mood"].dict()
    
    if "energy" in update_data and update_data["energy"]:
        update_data["energy"] = update_data["energy"].dict()
    
    if "stress" in update_data and update_data["stress"]:
        update_data["stress"] = update_data["stress"].dict()
    
    if "needs" in update_data and update_data["needs"]:
        update_data["needs"] = [need.dict() for need in update_data["needs"]]
    
    if not update_data:
        # Если нет данных для обновления, просто возвращаем существующую запись
        return StateSnapshotResponse.from_mongo(snapshot)
    
    # Обновляем запись
    success = await update_state_snapshot(snapshot_id, update_data)
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Ошибка при обновлении снимка состояния"
        )
    
    # Получаем обновленную запись
    updated_snapshot = await get_state_snapshot(snapshot_id)
    
    return StateSnapshotResponse.from_mongo(updated_snapshot)


@router.delete("/snapshots/{snapshot_id}", status_code=204)
async def delete_existing_state_snapshot(
    snapshot_id: str = Path(..., title="ID снимка состояния"),
    current_user: User = Depends(get_current_user)
):
    """
    Удаляет снимок состояния.
    """
    # Проверяем существование записи
    snapshot = await get_state_snapshot(snapshot_id)
    
    if not snapshot:
        raise HTTPException(
            status_code=404,
            detail="Снимок состояния не найден"
        )
    
    # Проверяем доступ пользователя
    if snapshot["user_id"] != str(current_user.id):
        raise HTTPException(
            status_code=403,
            detail="У вас нет доступа к этому снимку состояния"
        )
    
    # Удаляем запись
    success = await delete_state_snapshot(snapshot_id)
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Ошибка при удалении снимка состояния"
        )


@router.get("/snapshots/trends", response_model=Dict[str, List[Dict[str, Any]]])
async def get_state_trend_data(
    trends_query: StateTrendsQuery = Depends(),
    current_user: User = Depends(get_current_user)
):
    """
    Получает данные о трендах состояния пользователя.
    """
    try:
        trends = await get_state_trends(
            user_id=str(current_user.id),
            interval=trends_query.interval,
            indicators=trends_query.indicators,
            start_date=trends_query.start_date,
            end_date=trends_query.end_date,
            limit=trends_query.limit
        )
        
        return trends
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка при получении трендов состояния: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении трендов: {str(e)}"
        )


@router.get("/snapshots/needs-trends", response_model=Dict[str, List[Dict[str, Any]]])
async def get_needs_trend_data(
    needs_query: NeedsTrendsQuery = Depends(),
    current_user: User = Depends(get_current_user)
):
    """
    Получает данные о трендах удовлетворенности потребностей пользователя.
    """
    try:
        trends = await get_needs_satisfaction_trends(
            user_id=str(current_user.id),
            need_ids=needs_query.need_ids,
            start_date=needs_query.start_date,
            end_date=needs_query.end_date,
            interval=needs_query.interval,
            limit=needs_query.limit
        )
        
        return trends
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка при получении трендов потребностей: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении трендов: {str(e)}"
        )


@router.get("/snapshots/context-analysis", response_model=Dict[str, Any])
async def get_context_analysis(
    context_query: ContextAnalysisQuery = Depends(),
    current_user: User = Depends(get_current_user)
):
    """
    Получает анализ влияния контекстных факторов на состояние пользователя.
    """
    try:
        analysis = await get_context_factors_analysis(
            user_id=str(current_user.id),
            start_date=context_query.start_date,
            end_date=context_query.end_date
        )
        
        return analysis
    except Exception as e:
        logger.error(f"Ошибка при получении анализа контекстных факторов: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении анализа: {str(e)}"
        )