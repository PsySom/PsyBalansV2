"""
MongoDB схемы для хранения записей дневников настроения и мыслей.
Включает определения схем, валидаторы и индексы.
"""
from typing import Dict, Any, List
from datetime import datetime

# MongoDB схема для mood_entries (записи настроения и эмоций)
MOOD_ENTRIES_SCHEMA = {
    "validator": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "timestamp", "mood_score", "created_at"],
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
                    "description": "Время записи настроения"
                },
                "mood_score": {
                    "bsonType": "double",
                    "minimum": -10.0,
                    "maximum": 10.0,
                    "description": "Оценка настроения от -10 до +10"
                },
                "emotions": {
                    "bsonType": "array",
                    "description": "Список испытываемых эмоций с интенсивностью",
                    "items": {
                        "bsonType": "object",
                        "required": ["name", "intensity"],
                        "properties": {
                            "name": {
                                "bsonType": "string",
                                "description": "Название эмоции"
                            },
                            "intensity": {
                                "bsonType": "double",
                                "minimum": 0.0,
                                "maximum": 10.0,
                                "description": "Интенсивность эмоции от 0 до 10"
                            },
                            "category": {
                                "bsonType": "string",
                                "enum": ["positive", "neutral", "negative"],
                                "description": "Категория эмоции"
                            }
                        }
                    }
                },
                "triggers": {
                    "bsonType": "array",
                    "description": "Факторы, вызвавшие эмоции",
                    "items": {
                        "bsonType": "string"
                    }
                },
                "physical_sensations": {
                    "bsonType": "array",
                    "description": "Физические ощущения",
                    "items": {
                        "bsonType": "string"
                    }
                },
                "body_areas": {
                    "bsonType": "array",
                    "description": "Зоны тела с ощущениями",
                    "items": {
                        "bsonType": "string"
                    }
                },
                "context": {
                    "bsonType": "string",
                    "description": "Контекст записи"
                },
                "notes": {
                    "bsonType": "string",
                    "description": "Заметки пользователя"
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

# MongoDB схема для thought_entries (записи мыслей и самооценки)
THOUGHT_ENTRIES_SCHEMA = {
    "validator": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "timestamp", "situation", "created_at"],
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
                    "description": "Время записи мыслей"
                },
                "situation": {
                    "bsonType": "string",
                    "description": "Ситуация, вызвавшая мысли"
                },
                "automatic_thoughts": {
                    "bsonType": "array",
                    "description": "Список автоматических мыслей",
                    "items": {
                        "bsonType": "object",
                        "required": ["content", "belief_level"],
                        "properties": {
                            "content": {
                                "bsonType": "string",
                                "description": "Содержание мысли"
                            },
                            "belief_level": {
                                "bsonType": "double",
                                "minimum": 0.0,
                                "maximum": 100.0,
                                "description": "Уровень веры в мысль от 0 до 100"
                            },
                            "cognitive_distortions": {
                                "bsonType": "array",
                                "description": "Когнитивные искажения",
                                "items": {
                                    "bsonType": "string"
                                }
                            }
                        }
                    }
                },
                "emotions": {
                    "bsonType": "array",
                    "description": "Список испытываемых эмоций",
                    "items": {
                        "bsonType": "object",
                        "required": ["name", "intensity"],
                        "properties": {
                            "name": {
                                "bsonType": "string",
                                "description": "Название эмоции"
                            },
                            "intensity": {
                                "bsonType": "double",
                                "minimum": 0.0,
                                "maximum": 10.0,
                                "description": "Интенсивность эмоции от 0 до 10"
                            }
                        }
                    }
                },
                "evidence_for": {
                    "bsonType": "array",
                    "description": "Доказательства, подтверждающие мысль",
                    "items": {
                        "bsonType": "string"
                    }
                },
                "evidence_against": {
                    "bsonType": "array",
                    "description": "Доказательства, опровергающие мысль",
                    "items": {
                        "bsonType": "string"
                    }
                },
                "balanced_thought": {
                    "bsonType": "string",
                    "description": "Сбалансированная мысль"
                },
                "new_belief_level": {
                    "bsonType": "double",
                    "minimum": 0.0,
                    "maximum": 100.0,
                    "description": "Уровень веры в новую мысль от 0 до 100"
                },
                "action_plan": {
                    "bsonType": "string",
                    "description": "План действий"
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

# Индексы для mood_entries
MOOD_ENTRIES_INDEXES = [
    {"key": {"user_id": 1}, "name": "user_id_idx"},
    {"key": {"timestamp": -1}, "name": "timestamp_desc_idx"},
    {"key": {"user_id": 1, "timestamp": -1}, "name": "user_timestamp_idx"},
    {"key": {"mood_score": 1}, "name": "mood_score_idx"},
    {"key": {"emotions.category": 1}, "name": "emotions_category_idx"},
    {"key": {"created_at": -1}, "name": "created_at_idx"}
]

# Индексы для thought_entries
THOUGHT_ENTRIES_INDEXES = [
    {"key": {"user_id": 1}, "name": "user_id_idx"},
    {"key": {"timestamp": -1}, "name": "timestamp_desc_idx"},
    {"key": {"user_id": 1, "timestamp": -1}, "name": "user_timestamp_idx"},
    {"key": {"automatic_thoughts.cognitive_distortions": 1}, "name": "cognitive_distortions_idx"},
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
MOOD_ENTRY_EXAMPLE = {
    "user_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "timestamp": datetime.utcnow(),
    "mood_score": 7.5,
    "emotions": [
        {
            "name": "радость",
            "intensity": 8.5,
            "category": "positive"
        },
        {
            "name": "волнение",
            "intensity": 4.0,
            "category": "neutral"
        }
    ],
    "triggers": ["хорошие новости", "встреча с другом"],
    "physical_sensations": ["расслабленность", "легкость"],
    "body_areas": ["грудь", "лицо"],
    "context": "evening_check_in",
    "notes": "Сегодня был отличный день"
}

THOUGHT_ENTRY_EXAMPLE = {
    "user_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "timestamp": datetime.utcnow(),
    "situation": "Подготовка к важной презентации",
    "automatic_thoughts": [
        {
            "content": "Я не справлюсь с этой презентацией",
            "belief_level": 75.0,
            "cognitive_distortions": ["катастрофизация", "дихотомическое мышление"]
        }
    ],
    "emotions": [
        {
            "name": "тревога",
            "intensity": 7.0
        },
        {
            "name": "неуверенность",
            "intensity": 6.5
        }
    ],
    "evidence_for": ["Однажды я плохо выступил на презентации"],
    "evidence_against": ["Последние 5 презентаций прошли хорошо", "Я хорошо подготовился"],
    "balanced_thought": "Хотя я волнуюсь, у меня есть опыт и я хорошо подготовился к презентации",
    "new_belief_level": 30.0,
    "action_plan": "Сделать дыхательные упражнения перед выступлением, провести репетицию"
}