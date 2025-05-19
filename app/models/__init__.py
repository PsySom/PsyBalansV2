# models package initialization
# Импортируем модели для облегчения доступа к ним

from app.models.base import BaseModel
from app.models.user import User
from app.models.activity_types import ActivityType, ActivitySubtype
from app.models.needs import NeedCategory, Need
from app.models.activity import Activity, ActivityEvaluation, ActivityNeed
from app.models.calendar import UserCalendar, ActivitySchedule
from app.models.user_needs import UserNeed, UserNeedHistory, NeedFulfillmentPlan, NeedFulfillmentObjective
from app.models.user_state import UserState
from app.models.exercises import Exercise, Test, Practice, UserExerciseProgress

# Экспортируем модели, чтобы они были доступны при импорте из модуля
__all__ = [
    'BaseModel',
    'User',
    'ActivityType',
    'ActivitySubtype',
    'NeedCategory',
    'Need',
    'Activity',
    'ActivityEvaluation',
    'ActivityNeed',
    'UserCalendar',
    'ActivitySchedule',
    'UserNeed',
    'UserNeedHistory',
    'NeedFulfillmentPlan',
    'NeedFulfillmentObjective',
    'UserState',
    'Exercise',
    'Test',
    'Practice',
    'UserExerciseProgress',
]