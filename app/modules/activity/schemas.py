"""
Pydantic модели для API активностей.
"""
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, validator, root_validator


class ActivityBase(BaseModel):
    """Базовые поля активности"""
    title: str
    description: Optional[str] = None
    activity_type_id: Optional[UUID] = None
    activity_subtype_id: Optional[UUID] = None
    start_time: datetime
    end_time: datetime
    is_recurring: bool = False
    recurrence_pattern: Optional[Dict[str, Any]] = None
    priority: int = Field(default=2, ge=1, le=5)
    energy_required: int = Field(default=3, ge=1, le=5)
    color: Optional[str] = None
    location: Optional[str] = None
    tags: Optional[List[str]] = None

    @validator('end_time')
    def end_time_after_start_time(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('end_time must be after start_time')
        return v

    @validator('tags')
    def convert_tags_to_json(cls, v):
        if v is not None:
            return {"tags": v}
        return None


class ActivityCreate(ActivityBase):
    """Модель для создания активности"""
    parent_activity_id: Optional[UUID] = None
    user_id: Optional[UUID] = None  # может быть установлен из токена

    @root_validator
    def calculate_duration(cls, values):
        if 'start_time' in values and 'end_time' in values:
            values['duration_minutes'] = int((values['end_time'] - values['start_time']).total_seconds() / 60)
        return values


class ActivityUpdate(BaseModel):
    """Модель для обновления активности"""
    title: Optional[str] = None
    description: Optional[str] = None
    activity_type_id: Optional[UUID] = None
    activity_subtype_id: Optional[UUID] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_completed: Optional[bool] = None
    completion_time: Optional[datetime] = None
    is_recurring: Optional[bool] = None
    recurrence_pattern: Optional[Dict[str, Any]] = None
    priority: Optional[int] = Field(default=None, ge=1, le=5)
    energy_required: Optional[int] = Field(default=None, ge=1, le=5)
    color: Optional[str] = None
    location: Optional[str] = None
    tags: Optional[List[str]] = None


class ActivityResponse(ActivityBase):
    """Модель ответа для активности"""
    id: UUID
    user_id: UUID
    duration_minutes: int
    is_completed: bool
    completion_time: Optional[datetime] = None
    parent_activity_id: Optional[UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class ActivityFilter(BaseModel):
    """Параметры фильтрации активностей"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_completed: Optional[bool] = None
    activity_type_id: Optional[UUID] = None
    activity_subtype_id: Optional[UUID] = None
    priority: Optional[int] = None
    tags: Optional[List[str]] = None


class PaginationParams(BaseModel):
    """Параметры пагинации"""
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=10, ge=1, le=100)
    sort_by: Optional[str] = "start_time"
    sort_desc: bool = True


class ActivityTypeResponse(BaseModel):
    """Модель ответа для типа активности"""
    id: UUID
    name: str
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None

    class Config:
        orm_mode = True


class ActivitySubtypeResponse(BaseModel):
    """Модель ответа для подтипа активности"""
    id: UUID
    name: str
    description: Optional[str] = None
    activity_type_id: UUID
    color: Optional[str] = None
    icon: Optional[str] = None

    class Config:
        orm_mode = True


class ActivityNeedLinkBase(BaseModel):
    """Базовые поля связи активности с потребностью"""
    need_id: UUID
    strength: int = Field(default=3, ge=1, le=5)
    expected_impact: int = Field(default=3, ge=1, le=5)
    notes: Optional[str] = None


class ActivityNeedLinkCreate(ActivityNeedLinkBase):
    """Модель для создания связи активности с потребностью"""
    pass


class ActivityNeedLinkUpdate(BaseModel):
    """Модель для обновления связи активности с потребностью"""
    strength: Optional[int] = Field(default=None, ge=1, le=5)
    expected_impact: Optional[int] = Field(default=None, ge=1, le=5)
    actual_impact: Optional[int] = Field(default=None, ge=1, le=5)
    notes: Optional[str] = None


class ActivityNeedLinkResponse(ActivityNeedLinkBase):
    """Модель ответа для связи активности с потребностью"""
    id: UUID
    activity_id: UUID
    actual_impact: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class ActivityEvaluationBase(BaseModel):
    """Базовые поля оценки активности"""
    satisfaction_score: Optional[int] = Field(default=None, ge=1, le=10)
    enjoyment_score: Optional[int] = Field(default=None, ge=1, le=10)
    difficulty_score: Optional[int] = Field(default=None, ge=1, le=10)
    energy_change: Optional[int] = Field(default=None, ge=-5, le=5)
    mood_change: Optional[int] = Field(default=None, ge=-5, le=5)
    stress_level: Optional[int] = Field(default=None, ge=1, le=10)
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


class ActivityEvaluationCreate(ActivityEvaluationBase):
    """Модель для создания оценки активности"""
    activity_id: UUID


class ActivityEvaluationUpdate(ActivityEvaluationBase):
    """Модель для обновления оценки активности"""
    pass


class ActivityEvaluationResponse(ActivityEvaluationBase):
    """Модель ответа для оценки активности"""
    id: UUID
    activity_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True