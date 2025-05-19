"""
Pydantic-модели для валидации запросов и ответов API 
для работы с рекомендациями и интегративным дневником.
"""
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
from bson import ObjectId


class PyObjectId(str):
    """
    Класс для работы с MongoDB ObjectId через Pydantic.
    """
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            if not isinstance(v, str):
                return str(v)
            raise ValueError(f"Invalid ObjectId format: {v}")
        return str(v)


# Модели для рекомендаций
class RecommendationContextBase(BaseModel):
    state_snapshot_id: Optional[PyObjectId] = None
    trigger_type: str = Field(..., 
                             description="Тип триггера рекомендации",
                             example="need_deficit")
    priority_level: int = Field(..., ge=1, le=5, 
                              description="Уровень приоритета от 1 до 5",
                              example=3)


class RecommendedItemBase(BaseModel):
    item_id: str = Field(..., 
                        description="UUID объекта в строковом представлении",
                        example="b2c3d4e5-f6a7-8901-bcde-f12345678901")
    item_type: str = Field(..., 
                         description="Тип объекта",
                         example="physical_activity")
    relevance_score: float = Field(..., ge=0.0, le=1.0, 
                                 description="Оценка релевантности от 0 до 1",
                                 example=0.85)
    explanation: Optional[str] = Field(None, 
                                      description="Объяснение рекомендации",
                                      example="Эта активность хорошо подходит для удовлетворения потребности в движении")


class UserResponseBase(BaseModel):
    status: Optional[str] = Field(None, 
                                description="Статус ответа пользователя",
                                example="accepted")
    selected_item_id: Optional[str] = Field(None, 
                                          description="UUID выбранного объекта в строковом представлении",
                                          example="b2c3d4e5-f6a7-8901-bcde-f12345678901")
    response_time: Optional[datetime] = Field(None, 
                                            description="Время ответа",
                                            example="2024-05-18T12:30:00Z")
    user_feedback: Optional[str] = Field(None, 
                                       description="Обратная связь от пользователя",
                                       example="Хорошая рекомендация, спасибо")


class EffectivenessBase(BaseModel):
    state_improvement: Optional[float] = Field(None, ge=-1.0, le=1.0, 
                                             description="Улучшение состояния, от -1 до +1",
                                             example=0.6)
    user_rating: Optional[int] = Field(None, ge=1, le=5, 
                                     description="Оценка пользователя от 1 до 5",
                                     example=4)
    completion_status: Optional[str] = Field(None, 
                                           description="Статус выполнения",
                                           example="completed")


class RecommendationCreate(BaseModel):
    user_id: str = Field(..., 
                        description="UUID пользователя в строковом представлении",
                        example="a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    timestamp: datetime = Field(default_factory=datetime.utcnow,
                              description="Время создания рекомендации",
                              example="2024-05-18T12:00:00Z")
    context: RecommendationContextBase
    recommendation_type: str = Field(..., 
                                   description="Тип рекомендации",
                                   example="activity")
    recommended_items: List[RecommendedItemBase]
    user_response: Optional[UserResponseBase] = None
    effectiveness: Optional[EffectivenessBase] = None

    class Config:
        schema_extra = {
            "example": {
                "user_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "timestamp": "2024-05-18T12:00:00Z",
                "context": {
                    "state_snapshot_id": "5f8d5f66a9b9c0a1b2c3d4e5",
                    "trigger_type": "need_deficit",
                    "priority_level": 3
                },
                "recommendation_type": "activity",
                "recommended_items": [
                    {
                        "item_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                        "item_type": "physical_activity",
                        "relevance_score": 0.85,
                        "explanation": "Эта активность хорошо подходит для удовлетворения потребности в движении"
                    }
                ]
            }
        }


class RecommendationUpdate(BaseModel):
    user_response: Optional[UserResponseBase] = None
    effectiveness: Optional[EffectivenessBase] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Recommendation(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: str
    timestamp: datetime
    context: Dict[str, Any]
    recommendation_type: str
    recommended_items: List[Dict[str, Any]]
    user_response: Optional[Dict[str, Any]] = None
    effectiveness: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {
        "validate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {
            datetime: lambda dt: dt.isoformat(),
            ObjectId: lambda oid: str(oid),
        }
    }


class RecommendationResponse(BaseModel):
    """Модель для получения реакции пользователя на рекомендацию."""
    status: str = Field(..., 
                      description="Статус ответа (accepted, declined, postponed)",
                      example="accepted")
    selected_item_id: Optional[str] = Field(None, 
                                          description="ID выбранного элемента",
                                          example="b2c3d4e5-f6a7-8901-bcde-f12345678901")
    user_feedback: Optional[str] = Field(None, 
                                       description="Комментарий пользователя",
                                       example="Эта активность мне нравится")


class EffectivenessData(BaseModel):
    """Модель для оценки эффективности рекомендации."""
    state_improvement: float = Field(..., ge=-1.0, le=1.0, 
                                   description="Оценка улучшения состояния от -1 до 1",
                                   example=0.5)
    user_rating: int = Field(..., ge=1, le=5,
                           description="Оценка пользователя от 1 до 5",
                           example=4)
    completion_status: str = Field(...,
                                 description="Статус выполнения рекомендации",
                                 example="completed")


# Модели для интегративного дневника
class ConversationMessageBase(BaseModel):
    role: str = Field(..., 
                    description="Роль в диалоге",
                    example="system")
    content: str = Field(..., 
                       description="Содержание сообщения",
                       example="Как вы себя чувствуете сегодня?")
    timestamp: datetime = Field(default_factory=datetime.utcnow,
                              description="Время сообщения",
                              example="2024-05-18T12:00:00Z")


class NeedSatisfaction(BaseModel):
    need_id: str = Field(..., 
                        description="UUID потребности в строковом представлении",
                        example="d4e5f6a7-b8c9-0123-defg-234567890123")
    satisfaction_level: float = Field(..., ge=-5.0, le=5.0, 
                                    description="Уровень удовлетворенности потребности, от -5 до +5",
                                    example=3.0)


class ExtractedDataBase(BaseModel):
    mood: Optional[float] = Field(None, ge=-10.0, le=10.0, 
                                description="Настроение от -10 до +10",
                                example=6.5)
    emotions: Optional[List[str]] = Field(None, 
                                        description="Эмоции",
                                        example=["спокойствие", "расслабленность"])
    needs: Optional[List[NeedSatisfaction]] = Field(None, 
                                                 description="Потребности")
    thoughts: Optional[List[str]] = Field(None, 
                                        description="Мысли",
                                        example=["Медитация помогает снять тревогу"])
    action_items: Optional[List[str]] = Field(None, 
                                           description="Необходимые действия",
                                           example=["Продолжить практику медитации"])


class LinkedEntryBase(BaseModel):
    entry_type: str = Field(..., 
                          description="Тип связанной записи",
                          example="mood_tracking")
    entry_id: PyObjectId = Field(..., 
                               description="ID связанной записи",
                               example="6f7g8h9i-j0k1-2345-lmno-456789012345")


class DiaryEntryCreate(BaseModel):
    user_id: str = Field(..., 
                        description="UUID пользователя в строковом представлении",
                        example="a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    timestamp: datetime = Field(default_factory=datetime.utcnow,
                              description="Время записи в дневнике",
                              example="2024-05-18T12:00:00Z")
    session_id: Optional[str] = Field(None, 
                                    description="UUID сессии в строковом представлении",
                                    example="d4e5f6a7-b8c9-0123-defg-234567890123")
    entry_type: str = Field(..., 
                          description="Тип записи в дневнике",
                          example="reflection")
    conversation: List[ConversationMessageBase]
    extracted_data: Optional[ExtractedDataBase] = None
    linked_entries: Optional[List[LinkedEntryBase]] = None

    class Config:
        schema_extra = {
            "example": {
                "user_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "timestamp": "2024-05-18T12:00:00Z",
                "session_id": "d4e5f6a7-b8c9-0123-defg-234567890123",
                "entry_type": "reflection",
                "conversation": [
                    {
                        "role": "system",
                        "content": "Как вы себя чувствуете сегодня?",
                        "timestamp": "2024-05-18T12:00:00Z"
                    },
                    {
                        "role": "user",
                        "content": "Сегодня я чувствую себя спокойно и расслабленно, хотя утром была легкая тревога.",
                        "timestamp": "2024-05-18T12:01:00Z"
                    }
                ]
            }
        }


class DiaryEntryUpdate(BaseModel):
    conversation: Optional[List[ConversationMessageBase]] = None
    extracted_data: Optional[ExtractedDataBase] = None
    linked_entries: Optional[List[LinkedEntryBase]] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DiaryEntry(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: str
    timestamp: datetime
    session_id: Optional[str] = None
    entry_type: str
    conversation: List[Dict[str, Any]]
    extracted_data: Optional[Dict[str, Any]] = None
    linked_entries: Optional[List[Dict[str, Any]]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {
        "validate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {
            datetime: lambda dt: dt.isoformat(),
            ObjectId: lambda oid: str(oid),
        }
    }