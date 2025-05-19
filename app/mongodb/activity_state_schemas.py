"""
MongoDB схемы для хранения оценок активностей и снимков состояния пользователя.
Включает определения схем, валидаторы и индексы.
"""
from typing import Dict, Any, List
from datetime import datetime

# MongoDB схема для activity_evaluations (оценки выполненных активностей)
ACTIVITY_EVALUATIONS_SCHEMA = {
    "validator": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "activity_id", "timestamp", "completion_status", "created_at"],
            "properties": {
                "_id": {
                    "bsonType": "objectId",
                    "description": "Уникальный идентификатор записи"
                },
                "user_id": {
                    "bsonType": "string",
                    "description": "UUID пользователя в строковом представлении"
                },
                "activity_id": {
                    "bsonType": "string",
                    "description": "UUID активности в строковом представлении"
                },
                "schedule_id": {
                    "bsonType": "string",
                    "description": "UUID записи расписания в строковом представлении (опционально)"
                },
                "timestamp": {
                    "bsonType": "date",
                    "description": "Время оценки активности"
                },
                "completion_status": {
                    "bsonType": "string",
                    "enum": ["completed", "partial", "skipped"],
                    "description": "Статус выполнения активности"
                },
                "satisfaction_result": {
                    "bsonType": "double",
                    "minimum": 0.0,
                    "maximum": 10.0,
                    "description": "Удовлетворенность результатом, от 0 до 10"
                },
                "satisfaction_process": {
                    "bsonType": "double",
                    "minimum": 0.0,
                    "maximum": 10.0,
                    "description": "Удовлетворенность процессом, от 0 до 10"
                },
                "energy_impact": {
                    "bsonType": "double",
                    "minimum": -10.0,
                    "maximum": 10.0,
                    "description": "Влияние на энергию, от -10 до +10"
                },
                "stress_impact": {
                    "bsonType": "double",
                    "minimum": -10.0,
                    "maximum": 10.0,
                    "description": "Влияние на стресс, от -10 до +10"
                },
                "needs_impact": {
                    "bsonType": "array",
                    "description": "Влияние на потребности",
                    "items": {
                        "bsonType": "object",
                        "required": ["need_id", "impact_level"],
                        "properties": {
                            "need_id": {
                                "bsonType": "string",
                                "description": "UUID потребности в строковом представлении"
                            },
                            "impact_level": {
                                "bsonType": "double",
                                "minimum": -5.0,
                                "maximum": 5.0,
                                "description": "Уровень влияния на потребность, от -5 до +5"
                            }
                        }
                    }
                },
                "duration_minutes": {
                    "bsonType": "int",
                    "minimum": 0,
                    "description": "Фактическая продолжительность активности в минутах"
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

# MongoDB схема для state_snapshots (снимки состояния пользователя)
STATE_SNAPSHOTS_SCHEMA = {
    "validator": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "timestamp", "snapshot_type", "mood", "energy", "stress", "created_at"],
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
                    "description": "Время снимка состояния"
                },
                "snapshot_type": {
                    "bsonType": "string",
                    "enum": ["morning", "midday", "evening", "on_demand"],
                    "description": "Тип снимка состояния"
                },
                "mood": {
                    "bsonType": "object",
                    "required": ["score"],
                    "properties": {
                        "score": {
                            "bsonType": "double",
                            "minimum": -10.0,
                            "maximum": 10.0,
                            "description": "Оценка настроения, от -10 до +10"
                        },
                        "primary_emotions": {
                            "bsonType": "array",
                            "description": "Основные эмоции",
                            "items": {
                                "bsonType": "string"
                            }
                        },
                        "notes": {
                            "bsonType": "string",
                            "description": "Заметки о настроении"
                        }
                    }
                },
                "energy": {
                    "bsonType": "object",
                    "required": ["level"],
                    "properties": {
                        "level": {
                            "bsonType": "double",
                            "minimum": -10.0,
                            "maximum": 10.0,
                            "description": "Уровень энергии, от -10 до +10"
                        },
                        "physical_sensations": {
                            "bsonType": "array",
                            "description": "Физические ощущения",
                            "items": {
                                "bsonType": "string"
                            }
                        },
                        "notes": {
                            "bsonType": "string",
                            "description": "Заметки об энергии"
                        }
                    }
                },
                "stress": {
                    "bsonType": "object",
                    "required": ["level"],
                    "properties": {
                        "level": {
                            "bsonType": "double",
                            "minimum": 0.0,
                            "maximum": 10.0,
                            "description": "Уровень стресса, от 0 до 10"
                        },
                        "manifestations": {
                            "bsonType": "array",
                            "description": "Проявления стресса",
                            "items": {
                                "bsonType": "string"
                            }
                        },
                        "notes": {
                            "bsonType": "string",
                            "description": "Заметки о стрессе"
                        }
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
                            },
                            "notes": {
                                "bsonType": "string",
                                "description": "Заметки о потребности"
                            }
                        }
                    }
                },
                "focus_level": {
                    "bsonType": "double",
                    "minimum": 0.0,
                    "maximum": 10.0,
                    "description": "Уровень концентрации, от 0 до 10"
                },
                "sleep_quality": {
                    "bsonType": "double",
                    "minimum": 0.0,
                    "maximum": 10.0,
                    "description": "Качество сна, от 0 до 10"
                },
                "context_factors": {
                    "bsonType": "array",
                    "description": "Факторы контекста",
                    "items": {
                        "bsonType": "string"
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

# Индексы для activity_evaluations
ACTIVITY_EVALUATIONS_INDEXES = [
    {"key": {"user_id": 1}, "name": "user_id_idx"},
    {"key": {"timestamp": -1}, "name": "timestamp_desc_idx"},
    {"key": {"user_id": 1, "timestamp": -1}, "name": "user_timestamp_idx"},
    {"key": {"activity_id": 1}, "name": "activity_id_idx"},
    {"key": {"schedule_id": 1}, "name": "schedule_id_idx"},
    {"key": {"user_id": 1, "completion_status": 1}, "name": "user_completion_status_idx"},
    {"key": {"user_id": 1, "needs_impact.need_id": 1}, "name": "user_need_impact_idx"},
    {"key": {"created_at": -1}, "name": "created_at_idx"}
]

# Индексы для state_snapshots
STATE_SNAPSHOTS_INDEXES = [
    {"key": {"user_id": 1}, "name": "user_id_idx"},
    {"key": {"timestamp": -1}, "name": "timestamp_desc_idx"},
    {"key": {"user_id": 1, "timestamp": -1}, "name": "user_timestamp_idx"},
    {"key": {"user_id": 1, "snapshot_type": 1}, "name": "user_snapshot_type_idx"},
    {"key": {"user_id": 1, "needs.need_id": 1}, "name": "user_need_idx"},
    {"key": {"mood.score": 1}, "name": "mood_score_idx"},
    {"key": {"energy.level": 1}, "name": "energy_level_idx"},
    {"key": {"stress.level": 1}, "name": "stress_level_idx"},
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
ACTIVITY_EVALUATION_EXAMPLE = {
    "user_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "activity_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "schedule_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
    "timestamp": datetime.utcnow(),
    "completion_status": "completed",
    "satisfaction_result": 8.5,
    "satisfaction_process": 7.0,
    "energy_impact": 3.5,
    "stress_impact": -4.0,
    "needs_impact": [
        {
            "need_id": "d4e5f6a7-b8c9-0123-defg-234567890123",
            "impact_level": 3.5
        },
        {
            "need_id": "e5f6a7b8-c9d0-1234-efgh-345678901234",
            "impact_level": 2.0
        }
    ],
    "duration_minutes": 45,
    "notes": "Активность помогла расслабиться и снять напряжение."
}

STATE_SNAPSHOT_EXAMPLE = {
    "user_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "timestamp": datetime.utcnow(),
    "snapshot_type": "evening",
    "mood": {
        "score": 6.5,
        "primary_emotions": ["спокойствие", "удовлетворенность"],
        "notes": "Чувствую себя умиротворенно после прогулки"
    },
    "energy": {
        "level": -2.0,
        "physical_sensations": ["усталость", "расслабленность"],
        "notes": "Физически устал, но приятно"
    },
    "stress": {
        "level": 3.0,
        "manifestations": ["легкое напряжение в шее"],
        "notes": "Уровень стресса заметно снизился к вечеру"
    },
    "needs": [
        {
            "need_id": "d4e5f6a7-b8c9-0123-defg-234567890123",
            "satisfaction_level": 2.5,
            "notes": "Потребность в отдыхе удовлетворена"
        },
        {
            "need_id": "e5f6a7b8-c9d0-1234-efgh-345678901234",
            "satisfaction_level": -1.0,
            "notes": "Потребность в общении не удовлетворена"
        }
    ],
    "focus_level": 4.5,
    "sleep_quality": None,  # Будет заполнено утром
    "context_factors": ["хорошая погода", "завершил важные задачи"]
}