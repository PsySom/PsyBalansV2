"""
Pydantic модели для API дневников (настроения, мыслей, активностей).
"""
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, validator, root_validator


class MoodEntryBase(BaseModel):
    """Базовые поля записи настроения"""
    mood_score: float = Field(..., ge=-10.0, le=10.0, description="Оценка настроения от -10 до +10")
    emotions: List[Dict[str, Any]] = Field(..., description="Список испытываемых эмоций с интенсивностью")
    
    @validator('emotions')
    def validate_emotions(cls, v):
        if not v:
            raise ValueError("At least one emotion must be provided")
        
        for emotion in v:
            if 'name' not in emotion:
                raise ValueError("Each emotion must have a 'name' field")
            if 'intensity' not in emotion:
                raise ValueError("Each emotion must have an 'intensity' field")
            if not isinstance(emotion['intensity'], (int, float)) or not (0 <= emotion['intensity'] <= 10):
                raise ValueError("Emotion intensity must be a number between 0 and 10")
            if 'category' in emotion and emotion['category'] not in ['positive', 'neutral', 'negative']:
                raise ValueError("Emotion category must be one of: positive, neutral, negative")
        
        return v


class MoodEntryCreate(MoodEntryBase):
    """Модель для создания записи настроения"""
    timestamp: Optional[datetime] = Field(None, description="Время записи настроения")
    triggers: Optional[List[str]] = Field(None, description="Факторы, вызвавшие эмоции")
    physical_sensations: Optional[List[str]] = Field(None, description="Физические ощущения")
    body_areas: Optional[List[str]] = Field(None, description="Зоны тела с ощущениями")
    context: Optional[str] = Field(None, description="Контекст записи")
    notes: Optional[str] = Field(None, description="Заметки пользователя")
    
    @validator('timestamp', pre=True, always=True)
    def set_timestamp(cls, v):
        return v or datetime.now()


class MoodEntryUpdate(BaseModel):
    """Модель для обновления записи настроения"""
    mood_score: Optional[float] = Field(None, ge=-10.0, le=10.0)
    emotions: Optional[List[Dict[str, Any]]] = None
    triggers: Optional[List[str]] = None
    physical_sensations: Optional[List[str]] = None
    body_areas: Optional[List[str]] = None
    context: Optional[str] = None
    notes: Optional[str] = None


class MoodEntryResponse(BaseModel):
    """Модель ответа для записи настроения"""
    id: str
    user_id: str
    timestamp: datetime
    mood_score: float
    emotions: List[Dict[str, Any]]
    triggers: Optional[List[str]] = None
    physical_sensations: Optional[List[str]] = None
    body_areas: Optional[List[str]] = None
    context: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class ThoughtEntryBase(BaseModel):
    """Базовые поля записи мыслей"""
    situation: str = Field(..., description="Ситуация, вызвавшая мысли")
    automatic_thoughts: List[Dict[str, Any]] = Field(..., description="Список автоматических мыслей")
    emotions: List[Dict[str, Any]] = Field(..., description="Список испытываемых эмоций")
    
    @validator('automatic_thoughts')
    def validate_automatic_thoughts(cls, v):
        if not v:
            raise ValueError("At least one thought must be provided")
        
        for thought in v:
            if 'content' not in thought:
                raise ValueError("Each thought must have a 'content' field")
            if 'belief_level' not in thought:
                raise ValueError("Each thought must have a 'belief_level' field")
            if not isinstance(thought['belief_level'], (int, float)) or not (0 <= thought['belief_level'] <= 100):
                raise ValueError("Belief level must be a number between 0 and 100")
        
        return v
    
    @validator('emotions')
    def validate_emotions(cls, v):
        if not v:
            raise ValueError("At least one emotion must be provided")
        
        for emotion in v:
            if 'name' not in emotion:
                raise ValueError("Each emotion must have a 'name' field")
            if 'intensity' not in emotion:
                raise ValueError("Each emotion must have an 'intensity' field")
            if not isinstance(emotion['intensity'], (int, float)) or not (0 <= emotion['intensity'] <= 10):
                raise ValueError("Emotion intensity must be a number between 0 and 10")
        
        return v


class ThoughtEntryCreate(ThoughtEntryBase):
    """Модель для создания записи мыслей"""
    timestamp: Optional[datetime] = Field(None, description="Время записи мыслей")
    evidence_for: Optional[List[str]] = Field(None, description="Доказательства, подтверждающие мысль")
    evidence_against: Optional[List[str]] = Field(None, description="Доказательства, опровергающие мысль")
    balanced_thought: Optional[str] = Field(None, description="Сбалансированная мысль")
    new_belief_level: Optional[float] = Field(None, ge=0.0, le=100.0, description="Уровень веры в новую мысль от 0 до 100")
    action_plan: Optional[str] = Field(None, description="План действий")
    
    @validator('timestamp', pre=True, always=True)
    def set_timestamp(cls, v):
        return v or datetime.now()


class ThoughtEntryUpdate(BaseModel):
    """Модель для обновления записи мыслей"""
    situation: Optional[str] = None
    automatic_thoughts: Optional[List[Dict[str, Any]]] = None
    emotions: Optional[List[Dict[str, Any]]] = None
    evidence_for: Optional[List[str]] = None
    evidence_against: Optional[List[str]] = None
    balanced_thought: Optional[str] = None
    new_belief_level: Optional[float] = Field(None, ge=0.0, le=100.0)
    action_plan: Optional[str] = None


class ThoughtEntryResponse(BaseModel):
    """Модель ответа для записи мыслей"""
    id: str
    user_id: str
    timestamp: datetime
    situation: str
    automatic_thoughts: List[Dict[str, Any]]
    emotions: List[Dict[str, Any]]
    evidence_for: Optional[List[str]] = None
    evidence_against: Optional[List[str]] = None
    balanced_thought: Optional[str] = None
    new_belief_level: Optional[float] = None
    action_plan: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class ActivityEvaluationBase(BaseModel):
    """Базовые поля оценки активности"""
    satisfaction_score: Optional[int] = Field(None, ge=1, le=10, description="Общая удовлетворенность (1-10)")
    enjoyment_score: Optional[int] = Field(None, ge=1, le=10, description="Насколько понравилось (1-10)")
    difficulty_score: Optional[int] = Field(None, ge=1, le=10, description="Сложность (1-10)")
    energy_change: Optional[int] = Field(None, ge=-5, le=5, description="Изменение энергии (-5 до +5)")
    mood_change: Optional[int] = Field(None, ge=-5, le=5, description="Изменение настроения (-5 до +5)")
    stress_level: Optional[int] = Field(None, ge=1, le=10, description="Уровень стресса (1-10)")
    notes: Optional[str] = Field(None, description="Заметки пользователя")
    tags: Optional[List[str]] = Field(None, description="Теги, связанные с оценкой")


class ActivityEvaluationCreate(ActivityEvaluationBase):
    """Модель для создания оценки активности"""
    activity_id: UUID
    
    @validator('tags')
    def convert_tags_to_json(cls, v):
        if v is not None:
            return {"tags": v}
        return None


class ActivityEvaluationUpdate(ActivityEvaluationBase):
    """Модель для обновления оценки активности"""
    pass


class ActivityEvaluationResponse(ActivityEvaluationBase):
    """Модель ответа для оценки активности"""
    id: UUID
    activity_id: UUID
    tags: Optional[Dict[str, List[str]]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class DiaryEntryBase(BaseModel):
    """Базовые поля записи в интегративном дневнике"""
    entry_type: str = Field(..., description="Тип записи в дневнике")
    conversation: List[Dict[str, Any]] = Field(..., description="Диалог")
    
    @validator('entry_type')
    def validate_entry_type(cls, v):
        valid_types = ["check_in", "reflection", "mood_tracking", "thought_analysis", "need_assessment"]
        if v not in valid_types:
            raise ValueError(f"entry_type must be one of: {', '.join(valid_types)}")
        return v
    
    @validator('conversation')
    def validate_conversation(cls, v):
        if not v:
            raise ValueError("Conversation must have at least one message")
        
        for message in v:
            if 'role' not in message:
                raise ValueError("Each message must have a 'role' field")
            if message['role'] not in ['system', 'user']:
                raise ValueError("Role must be one of: system, user")
            if 'content' not in message:
                raise ValueError("Each message must have a 'content' field")
            if 'timestamp' not in message:
                message['timestamp'] = datetime.now()
        
        return v


class DiaryEntryCreate(DiaryEntryBase):
    """Модель для создания записи в интегративном дневнике"""
    timestamp: Optional[datetime] = Field(None, description="Время записи в дневнике")
    session_id: Optional[str] = Field(None, description="UUID сессии в строковом представлении")
    extracted_data: Optional[Dict[str, Any]] = Field(None, description="Извлеченные данные")
    linked_entries: Optional[List[Dict[str, Any]]] = Field(None, description="Связанные записи")
    
    @validator('timestamp', pre=True, always=True)
    def set_timestamp(cls, v):
        return v or datetime.now()


class DiaryEntryUpdate(BaseModel):
    """Модель для обновления записи в интегративном дневнике"""
    conversation: Optional[List[Dict[str, Any]]] = None
    extracted_data: Optional[Dict[str, Any]] = None
    linked_entries: Optional[List[Dict[str, Any]]] = None


class DiaryEntryResponse(BaseModel):
    """Модель ответа для записи в интегративном дневнике"""
    id: str
    user_id: str
    timestamp: datetime
    session_id: Optional[str] = None
    entry_type: str
    conversation: List[Dict[str, Any]]
    extracted_data: Optional[Dict[str, Any]] = None
    linked_entries: Optional[List[Dict[str, Any]]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class MoodFilter(BaseModel):
    """Параметры фильтрации записей настроения"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    min_score: Optional[float] = Field(None, ge=-10.0, le=10.0)
    max_score: Optional[float] = Field(None, ge=-10.0, le=10.0)
    context: Optional[str] = None
    
    @validator('max_score')
    def max_score_greater_than_min_score(cls, v, values):
        if v is not None and 'min_score' in values and values['min_score'] is not None:
            if v < values['min_score']:
                raise ValueError('max_score must be greater than or equal to min_score')
        return v


class ThoughtFilter(BaseModel):
    """Параметры фильтрации записей мыслей"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    situation_keywords: Optional[str] = None
    cognitive_distortions: Optional[List[str]] = None


class DiaryEntryFilter(BaseModel):
    """Параметры фильтрации записей дневника"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    entry_type: Optional[str] = None
    session_id: Optional[str] = None
    
    @validator('entry_type')
    def validate_entry_type(cls, v):
        if v is not None:
            valid_types = ["check_in", "reflection", "mood_tracking", "thought_analysis", "need_assessment"]
            if v not in valid_types:
                raise ValueError(f"entry_type must be one of: {', '.join(valid_types)}")
        return v


class DiaryStatisticsPeriod(BaseModel):
    """Параметры для получения статистики дневника"""
    period: str = Field("week", description="Период для статистики")
    end_date: Optional[datetime] = Field(None, description="Конечная дата периода")
    
    @validator('period')
    def validate_period(cls, v):
        valid_periods = ["day", "week", "month", "year", "all"]
        if v not in valid_periods:
            raise ValueError(f"period must be one of: {', '.join(valid_periods)}")
        return v