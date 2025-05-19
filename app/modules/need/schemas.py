"""
Pydantic модели для API потребностей.
"""
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, validator


class NeedCategoryBase(BaseModel):
    """Базовые поля категории потребностей"""
    name: str
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    display_order: int = 0


class NeedCategoryCreate(NeedCategoryBase):
    """Модель для создания категории потребностей"""
    pass


class NeedCategoryUpdate(BaseModel):
    """Модель для обновления категории потребностей"""
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    display_order: Optional[int] = None


class NeedCategoryResponse(NeedCategoryBase):
    """Модель ответа для категории потребностей"""
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class NeedBase(BaseModel):
    """Базовые поля потребности"""
    name: str
    description: Optional[str] = None
    category_id: UUID
    importance: int = Field(default=3, ge=1, le=5)
    is_custom: bool = False


class NeedCreate(NeedBase):
    """Модель для создания потребности"""
    user_id: Optional[UUID] = None  # может быть установлен из токена


class NeedUpdate(BaseModel):
    """Модель для обновления потребности"""
    name: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[UUID] = None
    importance: Optional[int] = Field(default=None, ge=1, le=5)
    is_custom: Optional[bool] = None


class NeedResponse(NeedBase):
    """Модель ответа для потребности"""
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    category: Optional[NeedCategoryResponse] = None

    class Config:
        orm_mode = True


class UserNeedBase(BaseModel):
    """Базовые поля персонализированной потребности пользователя"""
    need_id: UUID
    importance: float = Field(default=0.6, ge=0.0, le=1.0)
    target_satisfaction: float = Field(default=3.0, ge=-5.0, le=5.0)
    current_satisfaction: float = Field(default=0.0, ge=-5.0, le=5.0)
    is_favorite: bool = False
    custom_name: Optional[str] = None
    custom_description: Optional[str] = None
    custom_color: Optional[str] = None
    custom_icon: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class UserNeedCreate(UserNeedBase):
    """Модель для создания персонализированной потребности пользователя"""
    user_id: Optional[UUID] = None  # может быть установлен из токена


class UserNeedUpdate(BaseModel):
    """Модель для обновления персонализированной потребности пользователя"""
    importance: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    target_satisfaction: Optional[float] = Field(default=None, ge=-5.0, le=5.0)
    current_satisfaction: Optional[float] = Field(default=None, ge=-5.0, le=5.0)
    is_favorite: Optional[bool] = None
    custom_name: Optional[str] = None
    custom_description: Optional[str] = None
    custom_color: Optional[str] = None
    custom_icon: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class UserNeedResponse(UserNeedBase):
    """Модель ответа для персонализированной потребности пользователя"""
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    need: Optional[NeedResponse] = None

    class Config:
        orm_mode = True


class UserNeedSatisfactionUpdate(BaseModel):
    """Модель для обновления уровня удовлетворенности потребности"""
    satisfaction_level: float = Field(..., ge=-5.0, le=5.0)
    note: Optional[str] = None
    context: Optional[str] = None


class UserNeedHistoryResponse(BaseModel):
    """Модель ответа для истории потребностей пользователя"""
    id: UUID
    user_need_id: UUID
    user_id: UUID
    need_id: UUID
    satisfaction_level: float
    previous_value: Optional[float] = None
    change_value: Optional[float] = None
    activity_id: Optional[UUID] = None
    timestamp: datetime
    context: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime

    class Config:
        orm_mode = True


class UserNeedHistoryFilter(BaseModel):
    """Параметры фильтрации истории потребностей"""
    need_id: Optional[UUID] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    context: Optional[str] = None


class PaginationParams(BaseModel):
    """Параметры пагинации"""
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=10, ge=1, le=100)
    sort_by: Optional[str] = "timestamp"
    sort_desc: bool = True


class NeedFulfillmentPlanBase(BaseModel):
    """Базовые поля плана удовлетворения потребностей"""
    name: str
    description: Optional[str] = None
    start_date: datetime
    end_date: datetime
    status: str = "active"
    settings: Optional[Dict[str, Any]] = None

    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ['active', 'completed', 'cancelled', 'paused']
        if v not in valid_statuses:
            raise ValueError(f'status must be one of: {", ".join(valid_statuses)}')
        return v

    @validator('end_date')
    def end_date_after_start_date(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('end_date must be after start_date')
        return v


class NeedFulfillmentPlanCreate(NeedFulfillmentPlanBase):
    """Модель для создания плана удовлетворения потребностей"""
    user_id: Optional[UUID] = None  # может быть установлен из токена


class NeedFulfillmentPlanUpdate(BaseModel):
    """Модель для обновления плана удовлетворения потребностей"""
    name: Optional[str] = None
    description: Optional[str] = None
    end_date: Optional[datetime] = None
    status: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None

    @validator('status')
    def validate_status(cls, v):
        if v is not None:
            valid_statuses = ['active', 'completed', 'cancelled', 'paused']
            if v not in valid_statuses:
                raise ValueError(f'status must be one of: {", ".join(valid_statuses)}')
        return v


class NeedFulfillmentPlanResponse(NeedFulfillmentPlanBase):
    """Модель ответа для плана удовлетворения потребностей"""
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class NeedFulfillmentObjectiveBase(BaseModel):
    """Базовые поля цели в плане удовлетворения потребностей"""
    need_id: UUID
    user_need_id: UUID
    target_value: int = Field(..., ge=0, le=100)
    starting_value: int = Field(..., ge=0, le=100)
    current_value: int = Field(..., ge=0, le=100)
    status: str = "in_progress"
    priority: int = Field(default=3, ge=1, le=5)
    notes: Optional[str] = None

    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ['not_started', 'in_progress', 'completed', 'failed']
        if v not in valid_statuses:
            raise ValueError(f'status must be one of: {", ".join(valid_statuses)}')
        return v


class NeedFulfillmentObjectiveCreate(NeedFulfillmentObjectiveBase):
    """Модель для создания цели в плане удовлетворения потребностей"""
    plan_id: UUID
    user_id: Optional[UUID] = None  # может быть установлен из токена


class NeedFulfillmentObjectiveUpdate(BaseModel):
    """Модель для обновления цели в плане удовлетворения потребностей"""
    target_value: Optional[int] = Field(default=None, ge=0, le=100)
    current_value: Optional[int] = Field(default=None, ge=0, le=100)
    status: Optional[str] = None
    completion_date: Optional[datetime] = None
    priority: Optional[int] = Field(default=None, ge=1, le=5)
    notes: Optional[str] = None

    @validator('status')
    def validate_status(cls, v):
        if v is not None:
            valid_statuses = ['not_started', 'in_progress', 'completed', 'failed']
            if v not in valid_statuses:
                raise ValueError(f'status must be one of: {", ".join(valid_statuses)}')
        return v


class NeedFulfillmentObjectiveResponse(NeedFulfillmentObjectiveBase):
    """Модель ответа для цели в плане удовлетворения потребностей"""
    id: UUID
    plan_id: UUID
    user_id: UUID
    completion_date: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    progress: float

    class Config:
        orm_mode = True