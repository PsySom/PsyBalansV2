"""
Модуль репозиториев для доступа к данным.

Содержит базовые и специфические репозитории для работы с различными сущностями.
"""

from app.repositories.base_repository import BaseRepository
from app.repositories.activity_need_link_repository import ActivityNeedLinkRepository
from app.repositories.activity_repository import ActivityRepository
from app.repositories.activity_type_repository import ActivityTypeRepository
from app.repositories.activity_subtype_repository import ActivitySubtypeRepository
from app.repositories.need_repository import NeedRepository
from app.repositories.user_need_repository import UserNeedRepository

__all__ = [
    "BaseRepository",
    "ActivityNeedLinkRepository",
    "ActivityRepository",
    "ActivityTypeRepository",
    "ActivitySubtypeRepository",
    "NeedRepository",
    "UserNeedRepository"
]