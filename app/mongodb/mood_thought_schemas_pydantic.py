"""
Pydantic модели для валидации запросов и ответов, связанных с дневниками настроения и мыслей.
"""
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import uuid


# Общие базовые модели

class Emotion(BaseModel):
    """Модель эмоции с интенсивностью"""
    name: str = Field(..., min_length=1, max_length=100)
    intensity: float = Field(..., ge=0.0, le=10.0)
    category: Optional[str] = Field(None, pattern="^(positive|neutral|negative)$")


class EmotionSimple(BaseModel):
    """Упрощенная модель эмоции без категории"""
    name: str = Field(..., min_length=1, max_length=100)
    intensity: float = Field(..., ge=0.0, le=10.0)


class AutomaticThought(BaseModel):
    """Модель автоматической мысли с уровнем веры и искажениями"""
    content: str = Field(..., min_length=1)
    belief_level: float = Field(..., ge=0.0, le=100.0)
    cognitive_distortions: Optional[List[str]] = None


class TimestampedModel(BaseModel):
    """Базовая модель с временными метками"""
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


# Модели для запросов

class MoodEntryCreate(BaseModel):
    """Модель для создания записи настроения"""
    user_id: str
    mood_score: float = Field(..., ge=-10.0, le=10.0)
    emotions: List[Emotion]
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)
    triggers: Optional[List[str]] = None
    physical_sensations: Optional[List[str]] = None
    body_areas: Optional[List[str]] = None
    context: Optional[str] = None
    notes: Optional[str] = None

    @field_validator('user_id')
    @classmethod
    def validate_uuid(cls, v):
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError('user_id must be a valid UUID')


class MoodEntryUpdate(BaseModel):
    """Модель для обновления записи настроения"""
    mood_score: Optional[float] = Field(None, ge=-10.0, le=10.0)
    emotions: Optional[List[Emotion]] = None
    triggers: Optional[List[str]] = None
    physical_sensations: Optional[List[str]] = None
    body_areas: Optional[List[str]] = None
    context: Optional[str] = None
    notes: Optional[str] = None


class ThoughtEntryCreate(BaseModel):
    """Модель для создания записи мыслей"""
    user_id: str
    situation: str = Field(..., min_length=1)
    automatic_thoughts: List[AutomaticThought]
    emotions: List[EmotionSimple]
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)
    evidence_for: Optional[List[str]] = None
    evidence_against: Optional[List[str]] = None
    balanced_thought: Optional[str] = None
    new_belief_level: Optional[float] = Field(None, ge=0.0, le=100.0)
    action_plan: Optional[str] = None

    @field_validator('user_id')
    @classmethod
    def validate_uuid(cls, v):
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError('user_id must be a valid UUID')


class ThoughtEntryUpdate(BaseModel):
    """Модель для обновления записи мыслей"""
    situation: Optional[str] = None
    automatic_thoughts: Optional[List[AutomaticThought]] = None
    emotions: Optional[List[EmotionSimple]] = None
    evidence_for: Optional[List[str]] = None
    evidence_against: Optional[List[str]] = None
    balanced_thought: Optional[str] = None
    new_belief_level: Optional[float] = Field(None, ge=0.0, le=100.0)
    action_plan: Optional[str] = None


# Модели для ответов

class MoodEntryResponse(BaseModel):
    """Модель для ответа с записью настроения"""
    id: str
    user_id: str
    mood_score: float
    emotions: List[Emotion]
    timestamp: datetime
    triggers: Optional[List[str]] = None
    physical_sensations: Optional[List[str]] = None
    body_areas: Optional[List[str]] = None
    context: Optional[str] = None
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


class ThoughtEntryResponse(BaseModel):
    """Модель для ответа с записью мыслей"""
    id: str
    user_id: str
    situation: str
    automatic_thoughts: List[AutomaticThought]
    emotions: List[EmotionSimple]
    timestamp: datetime
    evidence_for: Optional[List[str]] = None
    evidence_against: Optional[List[str]] = None
    balanced_thought: Optional[str] = None
    new_belief_level: Optional[float] = None
    action_plan: Optional[str] = None
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

class EmotionFrequency(BaseModel):
    """Модель частоты эмоции"""
    name: str
    count: int


class TriggerFrequency(BaseModel):
    """Модель частоты триггера"""
    name: str
    count: int


class CognitiveDistortionFrequency(BaseModel):
    """Модель частоты когнитивного искажения"""
    name: str
    count: int


class MoodStatistics(BaseModel):
    """Модель статистики настроения"""
    period: str
    start_date: datetime
    end_date: datetime
    count: int
    mood_avg: Optional[float] = None
    mood_min: Optional[float] = None
    mood_max: Optional[float] = None
    top_emotions: List[EmotionFrequency]
    top_triggers: List[TriggerFrequency]


class ThoughtStatistics(BaseModel):
    """Модель статистики мыслей"""
    period: str
    start_date: datetime
    end_date: datetime
    count: int
    top_distortions: List[CognitiveDistortionFrequency]
    belief_change_avg: Optional[float] = None
    emotions_frequency: List[EmotionFrequency]


class MoodTrend(BaseModel):
    """Модель тренда настроения"""
    period: str
    avg_mood: float
    min_mood: float
    max_mood: float
    count: int
    date: datetime


# Модели для запросов статистики

class DateRangeQuery(BaseModel):
    """Модель запроса с диапазоном дат"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    @model_validator(mode='after')
    def check_dates(self):
        start_date = self.start_date
        end_date = self.end_date
        if start_date and end_date and start_date > end_date:
            raise ValueError('start_date должна быть раньше end_date')
        return self


class PaginationQuery(BaseModel):
    """Модель пагинации для запросов"""
    limit: int = Field(default=100, ge=1, le=1000)
    skip: int = Field(default=0, ge=0)
    sort_desc: bool = True  # True для сортировки от новых к старым


class StatisticsPeriodQuery(BaseModel):
    """Модель запроса для получения статистики за период"""
    period: str = Field(default="week", pattern="^(day|week|month|year|all)$")
    end_date: Optional[datetime] = None


class TrendQuery(BaseModel):
    """Модель запроса для получения трендов"""
    interval: str = Field(default="day", pattern="^(day|week|month)$")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=30, ge=1, le=100)
    
    @model_validator(mode='after')
    def check_dates(self):
        start_date = self.start_date
        end_date = self.end_date
        if start_date and end_date and start_date > end_date:
            raise ValueError('start_date должна быть раньше end_date')
        return self