"""
MongoDB схемы для хранения рекомендаций системы и записей интегративного дневника.
Включает определения схем, валидаторы и индексы.
"""
from typing import Dict, Any, List
from datetime import datetime

# MongoDB схема для recommendations (рекомендации системы)
RECOMMENDATIONS_SCHEMA = {
    "validator": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "timestamp", "context", "recommendation_type", "recommended_items", "created_at"],
            "properties": {
                "_id": {
                    "bsonType": "objectId",
                    "description": "Уникальный идентификатор записи"
                },
                "user_id": {
                    "bsonType": "string",
                    "description": "UUID пользователя в строковом представлении"
                },
                "timestamp": {
                    "bsonType": "date",
                    "description": "Время создания рекомендации"
                },
                "context": {
                    "bsonType": "object",
                    "required": ["trigger_type", "priority_level"],
                    "properties": {
                        "state_snapshot_id": {
                            "bsonType": "objectId",
                            "description": "Ссылка на снимок состояния"
                        },
                        "trigger_type": {
                            "bsonType": "string",
                            "enum": ["state_decline", "need_deficit", "scheduled", "user_request"],
                            "description": "Тип триггера рекомендации"
                        },
                        "priority_level": {
                            "bsonType": "int",
                            "minimum": 1,
                            "maximum": 5,
                            "description": "Уровень приоритета от 1 до 5"
                        }
                    }
                },
                "recommendation_type": {
                    "bsonType": "string",
                    "enum": ["activity", "exercise", "practice", "test", "need_satisfaction"],
                    "description": "Тип рекомендации"
                },
                "recommended_items": {
                    "bsonType": "array",
                    "description": "Рекомендуемые объекты",
                    "items": {
                        "bsonType": "object",
                        "required": ["item_id", "item_type", "relevance_score"],
                        "properties": {
                            "item_id": {
                                "bsonType": "string",
                                "description": "UUID объекта в строковом представлении"
                            },
                            "item_type": {
                                "bsonType": "string",
                                "description": "Тип объекта"
                            },
                            "relevance_score": {
                                "bsonType": "double",
                                "minimum": 0.0,
                                "maximum": 1.0,
                                "description": "Оценка релевантности от 0 до 1"
                            },
                            "explanation": {
                                "bsonType": "string",
                                "description": "Объяснение рекомендации"
                            }
                        }
                    }
                },
                "user_response": {
                    "bsonType": "object",
                    "properties": {
                        "status": {
                            "bsonType": "string",
                            "enum": ["accepted", "declined", "postponed", "no_response"],
                            "description": "Статус ответа пользователя"
                        },
                        "selected_item_id": {
                            "bsonType": "string",
                            "description": "UUID выбранного объекта в строковом представлении"
                        },
                        "response_time": {
                            "bsonType": "date",
                            "description": "Время ответа"
                        },
                        "user_feedback": {
                            "bsonType": "string",
                            "description": "Обратная связь от пользователя"
                        }
                    }
                },
                "effectiveness": {
                    "bsonType": "object",
                    "properties": {
                        "state_improvement": {
                            "bsonType": "double",
                            "minimum": -1.0,
                            "maximum": 1.0,
                            "description": "Улучшение состояния, от -1 до +1"
                        },
                        "user_rating": {
                            "bsonType": "int",
                            "minimum": 1,
                            "maximum": 5,
                            "description": "Оценка пользователя от 1 до 5"
                        },
                        "completion_status": {
                            "bsonType": "string",
                            "description": "Статус выполнения"
                        }
                    }
                },
                "created_at": {
                    "bsonType": "date",
                    "description": "Время создания записи"
                },
                "updated_at": {
                    "bsonType": "date",
                    "description": "Время последнего обновления записи"
                }
            }
        }
    }
}

# MongoDB схема для diary_entries (интегративный дневник)
DIARY_ENTRIES_SCHEMA = {
    "validator": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "timestamp", "entry_type", "conversation", "created_at"],
            "properties": {
                "_id": {
                    "bsonType": "objectId",
                    "description": "Уникальный идентификатор записи"
                },
                "user_id": {
                    "bsonType": "string",
                    "description": "UUID пользователя в строковом представлении"
                },
                "timestamp": {
                    "bsonType": "date",
                    "description": "Время записи в дневнике"
                },
                "session_id": {
                    "bsonType": "string",
                    "description": "UUID сессии в строковом представлении"
                },
                "entry_type": {
                    "bsonType": "string",
                    "enum": ["check_in", "reflection", "mood_tracking", "thought_analysis", "need_assessment"],
                    "description": "Тип записи в дневнике"
                },
                "conversation": {
                    "bsonType": "array",
                    "description": "Диалог",
                    "items": {
                        "bsonType": "object",
                        "required": ["role", "content", "timestamp"],
                        "properties": {
                            "role": {
                                "bsonType": "string",
                                "enum": ["system", "user"],
                                "description": "Роль в диалоге"
                            },
                            "content": {
                                "bsonType": "string",
                                "description": "Содержание сообщения"
                            },
                            "timestamp": {
                                "bsonType": "date",
                                "description": "Время сообщения"
                            }
                        }
                    }
                },
                "extracted_data": {
                    "bsonType": "object",
                    "properties": {
                        "mood": {
                            "bsonType": "double",
                            "minimum": -10.0,
                            "maximum": 10.0,
                            "description": "Настроение от -10 до +10"
                        },
                        "emotions": {
                            "bsonType": "array",
                            "description": "Эмоции",
                            "items": {
                                "bsonType": "string"
                            }
                        },
                        "needs": {
                            "bsonType": "array",
                            "description": "Потребности",
                            "items": {
                                "bsonType": "object",
                                "required": ["need_id", "satisfaction_level"],
                                "properties": {
                                    "need_id": {
                                        "bsonType": "string",
                                        "description": "UUID потребности в строковом представлении"
                                    },
                                    "satisfaction_level": {
                                        "bsonType": "double",
                                        "minimum": -5.0,
                                        "maximum": 5.0,
                                        "description": "Уровень удовлетворенности потребности, от -5 до +5"
                                    }
                                }
                            }
                        },
                        "thoughts": {
                            "bsonType": "array",
                            "description": "Мысли",
                            "items": {
                                "bsonType": "string"
                            }
                        },
                        "action_items": {
                            "bsonType": "array",
                            "description": "Необходимые действия",
                            "items": {
                                "bsonType": "string"
                            }
                        }
                    }
                },
                "linked_entries": {
                    "bsonType": "array",
                    "description": "Связанные записи",
                    "items": {
                        "bsonType": "object",
                        "required": ["entry_type", "entry_id"],
                        "properties": {
                            "entry_type": {
                                "bsonType": "string",
                                "description": "Тип связанной записи"
                            },
                            "entry_id": {
                                "bsonType": "objectId",
                                "description": "ID связанной записи"
                            }
                        }
                    }
                },
                "created_at": {
                    "bsonType": "date",
                    "description": "Время создания записи"
                },
                "updated_at": {
                    "bsonType": "date",
                    "description": "Время последнего обновления записи"
                }
            }
        }
    }
}

# Индексы для recommendations
RECOMMENDATIONS_INDEXES = [
    {"key": {"user_id": 1}, "name": "user_id_idx"},
    {"key": {"timestamp": -1}, "name": "timestamp_desc_idx"},
    {"key": {"user_id": 1, "timestamp": -1}, "name": "user_timestamp_idx"},
    {"key": {"context.state_snapshot_id": 1}, "name": "state_snapshot_id_idx"},
    {"key": {"context.trigger_type": 1}, "name": "trigger_type_idx"},
    {"key": {"recommendation_type": 1}, "name": "recommendation_type_idx"},
    {"key": {"recommended_items.item_id": 1}, "name": "item_id_idx"},
    {"key": {"user_response.status": 1}, "name": "response_status_idx"},
    {"key": {"created_at": -1}, "name": "created_at_idx"}
]

# Индексы для diary_entries
DIARY_ENTRIES_INDEXES = [
    {"key": {"user_id": 1}, "name": "user_id_idx"},
    {"key": {"timestamp": -1}, "name": "timestamp_desc_idx"},
    {"key": {"user_id": 1, "timestamp": -1}, "name": "user_timestamp_idx"},
    {"key": {"session_id": 1}, "name": "session_id_idx"},
    {"key": {"entry_type": 1}, "name": "entry_type_idx"},
    {"key": {"extracted_data.mood": 1}, "name": "mood_idx"},
    {"key": {"extracted_data.needs.need_id": 1}, "name": "needs_idx"},
    {"key": {"linked_entries.entry_id": 1}, "name": "linked_entries_idx"},
    {"key": {"created_at": -1}, "name": "created_at_idx"}
]

# Функция для формирования базового документа с временными метками
def create_timestamped_document(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Добавляет временные метки created_at и updated_at к документу.
    Если они уже есть, не перезаписывает created_at.
    """
    now = datetime.utcnow()
    
    if 'created_at' not in data:
        data['created_at'] = now
    
    data['updated_at'] = now
    
    return data


# Примеры документов для тестирования и документации
RECOMMENDATION_EXAMPLE = {
    "user_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "timestamp": datetime.utcnow(),
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
        },
        {
            "item_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
            "item_type": "social_activity",
            "relevance_score": 0.7,
            "explanation": "Эта активность поможет удовлетворить потребность в общении"
        }
    ],
    "user_response": {
        "status": "accepted",
        "selected_item_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
        "response_time": datetime.utcnow(),
        "user_feedback": "Хорошая рекомендация, спасибо"
    },
    "effectiveness": {
        "state_improvement": 0.6,
        "user_rating": 4,
        "completion_status": "completed"
    }
}

DIARY_ENTRY_EXAMPLE = {
    "user_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "timestamp": datetime.utcnow(),
    "session_id": "d4e5f6a7-b8c9-0123-defg-234567890123",
    "entry_type": "reflection",
    "conversation": [
        {
            "role": "system",
            "content": "Как вы себя чувствуете сегодня?",
            "timestamp": datetime.utcnow()
        },
        {
            "role": "user",
            "content": "Сегодня я чувствую себя спокойно и расслабленно, хотя утром была легкая тревога.",
            "timestamp": datetime.utcnow()
        },
        {
            "role": "system",
            "content": "Что помогло вам справиться с утренней тревогой?",
            "timestamp": datetime.utcnow()
        },
        {
            "role": "user",
            "content": "Мне помогла утренняя медитация и прогулка на свежем воздухе.",
            "timestamp": datetime.utcnow()
        }
    ],
    "extracted_data": {
        "mood": 6.5,
        "emotions": ["спокойствие", "расслабленность", "легкая тревога"],
        "needs": [
            {
                "need_id": "d4e5f6a7-b8c9-0123-defg-234567890123",
                "satisfaction_level": 3.0
            },
            {
                "need_id": "e5f6a7b8-c9d0-1234-efgh-345678901234",
                "satisfaction_level": 2.0
            }
        ],
        "thoughts": ["Медитация помогает снять тревогу", "Свежий воздух улучшает настроение"],
        "action_items": ["Продолжить практику медитации", "Ежедневно гулять на свежем воздухе"]
    },
    "linked_entries": [
        {
            "entry_type": "mood_tracking",
            "entry_id": "6f7g8h9i-j0k1-2345-lmno-456789012345"
        }
    ]
}