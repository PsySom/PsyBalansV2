"""
Pydantic модели для API календаря и расписания активностей.
"""
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
from uuid import UUID
from pydantic import BaseModel, Field, validator, root_validator


class CalendarBase(BaseModel):
    """Базовые поля календаря пользователя"""
    name: str
    description: Optional[str] = None
    color: Optional[str] = Field(None, regex=r'^#[0-9a-fA-F]{6}$')  # HEX-код цвета
    is_default: bool = False
    is_shared: bool = False
    settings: Optional[Dict[str, Any]] = None


class CalendarCreate(CalendarBase):
    """Модель для создания календаря пользователя"""
    user_id: Optional[UUID] = None  # Может быть установлен из токена


class CalendarUpdate(BaseModel):
    """Модель для обновления календаря пользователя"""
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = Field(None, regex=r'^#[0-9a-fA-F]{6}$')
    is_default: Optional[bool] = None
    is_shared: Optional[bool] = None
    settings: Optional[Dict[str, Any]] = None


class CalendarResponse(CalendarBase):
    """Модель ответа для календаря пользователя"""
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class ActivityScheduleBase(BaseModel):
    """Базовые поля расписания активности"""
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    all_day: bool = False
    priority: int = Field(default=2, ge=1, le=5)
    is_flexible: bool = False
    location: Optional[str] = None
    reminders: Optional[List[Dict[str, Any]]] = None
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


class ActivityScheduleCreate(ActivityScheduleBase):
    """Модель для создания расписания активности"""
    calendar_id: UUID
    activity_id: Optional[UUID] = None
    user_id: Optional[UUID] = None  # Может быть установлен из токена
    is_recurring: bool = False
    recurrence_pattern: Optional[Dict[str, Any]] = None

    @root_validator
    def calculate_duration(cls, values):
        if 'start_time' in values and 'end_time' in values:
            values['duration_minutes'] = int((values['end_time'] - values['start_time']).total_seconds() / 60)
        return values


class ActivityScheduleUpdate(BaseModel):
    """Модель для обновления расписания активности"""
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    all_day: Optional[bool] = None
    status: Optional[str] = None
    priority: Optional[int] = Field(default=None, ge=1, le=5)
    is_flexible: Optional[bool] = None
    location: Optional[str] = None
    reminders: Optional[List[Dict[str, Any]]] = None
    tags: Optional[List[str]] = None
    
    @validator('status')
    def validate_status(cls, v):
        if v is not None:
            valid_statuses = ['scheduled', 'in_progress', 'completed', 'cancelled', 'postponed']
            if v not in valid_statuses:
                raise ValueError(f'status must be one of: {", ".join(valid_statuses)}')
        return v


class ActivityScheduleResponse(ActivityScheduleBase):
    """Модель ответа для расписания активности"""
    id: UUID
    calendar_id: UUID
    activity_id: Optional[UUID] = None
    user_id: UUID
    duration_minutes: int
    status: str
    completion_time: Optional[datetime] = None
    is_recurring: bool
    recurrence_pattern: Optional[Dict[str, Any]] = None
    recurrence_parent_id: Optional[UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class RescheduleData(BaseModel):
    """Модель данных для перепланирования активности"""
    start_time: datetime
    end_time: Optional[datetime] = None
    
    @validator('end_time', always=True)
    def set_end_time(cls, v, values):
        if v is None and 'start_time' in values:
            # Если end_time не указано, устанавливаем его на час после start_time
            return values['start_time'] + timedelta(hours=1)
        return v


class CompletionData(BaseModel):
    """Модель данных для отметки активности как выполненной"""
    completion_time: Optional[datetime] = None
    notes: Optional[str] = None
    satisfaction_score: Optional[int] = Field(None, ge=1, le=10)
    
    @validator('completion_time', always=True)
    def set_completion_time(cls, v):
        if v is None:
            return datetime.now()
        return v


class RecurringActivityCreate(ActivityScheduleBase):
    """Модель для создания повторяющейся активности"""
    calendar_id: UUID
    activity_id: Optional[UUID] = None
    user_id: Optional[UUID] = None  # Может быть установлен из токена
    recurrence_pattern: Dict[str, Any] = Field(..., description="Паттерн повторения активности")
    start_date: datetime = Field(..., description="Дата начала серии повторений")
    end_date: Optional[datetime] = Field(None, description="Дата окончания серии повторений")
    occurrences: Optional[int] = Field(None, description="Количество повторений (альтернатива end_date)")
    
    @validator('recurrence_pattern')
    def validate_recurrence_pattern(cls, v):
        required_fields = ['frequency']
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Field '{field}' is required in recurrence_pattern")
        
        valid_frequencies = ['daily', 'weekly', 'monthly', 'yearly']
        if v['frequency'] not in valid_frequencies:
            raise ValueError(f"frequency must be one of: {', '.join(valid_frequencies)}")
        
        return v
    
    @validator('occurrences')
    def validate_occurrences(cls, v, values):
        if v is not None and 'end_date' in values and values['end_date'] is not None:
            raise ValueError("Only one of occurrences or end_date should be provided")
        return v


class CalendarFilter(BaseModel):
    """Параметры фильтрации календарей"""
    is_default: Optional[bool] = None
    is_shared: Optional[bool] = None


class ScheduleFilter(BaseModel):
    """Параметры фильтрации расписания"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[str] = None
    activity_id: Optional[UUID] = None
    calendar_id: Optional[UUID] = None
    priority: Optional[int] = None
    is_recurring: Optional[bool] = None
    all_day: Optional[bool] = None
    
    @validator('status')
    def validate_status(cls, v):
        if v is not None:
            valid_statuses = ['scheduled', 'in_progress', 'completed', 'cancelled', 'postponed']
            if v not in valid_statuses:
                raise ValueError(f'status must be one of: {", ".join(valid_statuses)}')
        return v


class PaginationParams(BaseModel):
    """Параметры пагинации"""
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=10, ge=1, le=100)
    sort_by: Optional[str] = "start_time"
    sort_desc: bool = True