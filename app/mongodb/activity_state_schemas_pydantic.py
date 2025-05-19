"""
Pydantic модели для валидации запросов и ответов, связанных с оценками активностей и состояниями пользователя.
"""
from pydantic import BaseModel, Field, validator, model_validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import uuid


# Общие базовые модели

class NeedImpact(BaseModel):
    """Модель для влияния активности на потребность"""
    need_id: str = Field(..., min_length=36, max_length=36)
    impact_level: float = Field(..., ge=-5.0, le=5.0)

    @validator('need_id')
    def validate_uuid(cls, v):
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError('need_id must be a valid UUID')


class NeedSatisfaction(BaseModel):
    """Модель для уровня удовлетворенности потребности"""
    need_id: str = Field(..., min_length=36, max_length=36)
    satisfaction_level: float = Field(..., ge=-5.0, le=5.0)
    notes: Optional[str] = None

    @validator('need_id')
    def validate_uuid(cls, v):
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError('need_id must be a valid UUID')


class TimestampedModel(BaseModel):
    """Базовая модель с временными метками"""
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


class MoodData(BaseModel):
    """Модель данных о настроении"""
    score: float = Field(..., ge=-10.0, le=10.0)
    primary_emotions: Optional[List[str]] = Field(default_factory=list)
    notes: Optional[str] = None


class EnergyData(BaseModel):
    """Модель данных об энергии"""
    level: float = Field(..., ge=-10.0, le=10.0)
    physical_sensations: Optional[List[str]] = Field(default_factory=list)
    notes: Optional[str] = None


class StressData(BaseModel):
    """Модель данных о стрессе"""
    level: float = Field(..., ge=0.0, le=10.0)
    manifestations: Optional[List[str]] = Field(default_factory=list)
    notes: Optional[str] = None


# Модели для запросов

class ActivityEvaluationCreate(BaseModel):
    """Модель для создания оценки активности"""
    user_id: str
    activity_id: str
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)
    completion_status: str = Field(..., pattern="^(completed|partial|skipped)$")
    schedule_id: Optional[str] = None
    satisfaction_result: Optional[float] = Field(None, ge=0.0, le=10.0)
    satisfaction_process: Optional[float] = Field(None, ge=0.0, le=10.0)
    energy_impact: Optional[float] = Field(None, ge=-10.0, le=10.0)
    stress_impact: Optional[float] = Field(None, ge=-10.0, le=10.0)
    needs_impact: Optional[List[NeedImpact]] = None
    duration_minutes: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None

    @validator('user_id', 'activity_id')
    def validate_uuid(cls, v, values, **kwargs):
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            field_name = kwargs.get('field_name', 'id')
            raise ValueError(f'{field_name} must be a valid UUID')

    @validator('schedule_id')
    def validate_optional_uuid(cls, v):
        if v is not None:
            try:
                uuid.UUID(v)
                return v
            except ValueError:
                raise ValueError('schedule_id must be a valid UUID if provided')
        return v


class ActivityEvaluationUpdate(BaseModel):
    """Модель для обновления оценки активности"""
    completion_status: Optional[str] = Field(None, pattern="^(completed|partial|skipped)$")
    satisfaction_result: Optional[float] = Field(None, ge=0.0, le=10.0)
    satisfaction_process: Optional[float] = Field(None, ge=0.0, le=10.0)
    energy_impact: Optional[float] = Field(None, ge=-10.0, le=10.0)
    stress_impact: Optional[float] = Field(None, ge=-10.0, le=10.0)
    needs_impact: Optional[List[NeedImpact]] = None
    duration_minutes: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None


class StateSnapshotCreate(BaseModel):
    """Модель для создания снимка состояния"""
    user_id: str
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)
    snapshot_type: str = Field(..., pattern="^(morning|midday|evening|on_demand)$")
    mood: MoodData
    energy: EnergyData
    stress: StressData
    needs: Optional[List[NeedSatisfaction]] = None
    focus_level: Optional[float] = Field(None, ge=0.0, le=10.0)
    sleep_quality: Optional[float] = Field(None, ge=0.0, le=10.0)
    context_factors: Optional[List[str]] = None

    @validator('user_id')
    def validate_uuid(cls, v):
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError('user_id must be a valid UUID')


class StateSnapshotUpdate(BaseModel):
    """Модель для обновления снимка состояния"""
    mood: Optional[MoodData] = None
    energy: Optional[EnergyData] = None
    stress: Optional[StressData] = None
    needs: Optional[List[NeedSatisfaction]] = None
    focus_level: Optional[float] = Field(None, ge=0.0, le=10.0)
    sleep_quality: Optional[float] = Field(None, ge=0.0, le=10.0)
    context_factors: Optional[List[str]] = None


# Модели для ответов

class ActivityEvaluationResponse(BaseModel):
    """Модель для ответа с оценкой активности"""
    id: str
    user_id: str
    activity_id: str
    timestamp: datetime
    completion_status: str
    schedule_id: Optional[str] = None
    satisfaction_result: Optional[float] = None
    satisfaction_process: Optional[float] = None
    energy_impact: Optional[float] = None
    stress_impact: Optional[float] = None
    needs_impact: Optional[List[NeedImpact]] = None
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
        "validate_by_name": True,
        "json_encoders": {
            datetime: lambda dt: dt.isoformat()
        }
    }
    
    @classmethod
    def from_mongo(cls, mongo_doc: Dict[str, Any]):
        """Преобразует документ MongoDB в модель Pydantic"""
        # Преобразуем _id из ObjectId в строку
        if '_id' in mongo_doc:
            mongo_doc['id'] = str(mongo_doc.pop('_id'))
        return cls(**mongo_doc)


class StateSnapshotResponse(BaseModel):
    """Модель для ответа со снимком состояния"""
    id: str
    user_id: str
    timestamp: datetime
    snapshot_type: str
    mood: MoodData
    energy: EnergyData
    stress: StressData
    needs: Optional[List[NeedSatisfaction]] = None
    focus_level: Optional[float] = None
    sleep_quality: Optional[float] = None
    context_factors: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
        "validate_by_name": True,
        "json_encoders": {
            datetime: lambda dt: dt.isoformat()
        }
    }
    
    @classmethod
    def from_mongo(cls, mongo_doc: Dict[str, Any]):
        """Преобразует документ MongoDB в модель Pydantic"""
        # Преобразуем _id из ObjectId в строку
        if '_id' in mongo_doc:
            mongo_doc['id'] = str(mongo_doc.pop('_id'))
        return cls(**mongo_doc)


# Модели для статистики и анализа

class DateRangeQuery(BaseModel):
    """Модель запроса с диапазоном дат"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    @model_validator(mode='after')
    def check_dates(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError('start_date должна быть раньше end_date')
        return self


class PaginationQuery(BaseModel):
    """Модель пагинации для запросов"""
    limit: int = Field(default=100, ge=1, le=1000)
    skip: int = Field(default=0, ge=0)
    sort_desc: bool = True  # True для сортировки от новых к старым


class ActivityStatisticsQuery(BaseModel):
    """Модель запроса для получения статистики по активностям"""
    period: str = Field(default="month", pattern="^(week|month|year)$")
    need_id: Optional[str] = None
    end_date: Optional[datetime] = None

    @validator('need_id')
    def validate_optional_uuid(cls, v):
        if v is not None:
            try:
                uuid.UUID(v)
                return v
            except ValueError:
                raise ValueError('need_id must be a valid UUID if provided')
        return v


class StateTrendsQuery(BaseModel):
    """Модель запроса для получения трендов состояния"""
    interval: str = Field(default="day", pattern="^(day|week|month)$")
    indicators: List[str] = Field(default=["mood", "energy", "stress"])
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=30, ge=1, le=100)
    
    @model_validator(mode='after')
    def check_dates(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError('start_date должна быть раньше end_date')
        return self


class NeedsTrendsQuery(BaseModel):
    """Модель запроса для получения трендов потребностей"""
    need_ids: Optional[List[str]] = None
    interval: str = Field(default="day", pattern="^(day|week|month)$")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=30, ge=1, le=100)
    
    @validator('need_ids')
    def validate_need_ids(cls, v):
        if v is not None:
            for need_id in v:
                try:
                    uuid.UUID(need_id)
                except ValueError:
                    raise ValueError('All need_ids must be valid UUIDs')
        return v
    
    @model_validator(mode='after')
    def check_dates(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError('start_date должна быть раньше end_date')
        return self


class ContextAnalysisQuery(BaseModel):
    """Модель запроса для анализа контекстных факторов"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    @model_validator(mode='after')
    def check_dates(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError('start_date должна быть раньше end_date')
        return self