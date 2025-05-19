import pytest
from sqlalchemy import inspect
from app.models import (
    User, ActivityType, ActivitySubtype, NeedCategory, Need,
    Activity, ActivityEvaluation, ActivityNeed
)
from app.core.database.postgresql import Base


def get_model_columns(model):
    """Получает список колонок модели"""
    inspector = inspect(model)
    return set(c.key for c in inspector.columns)


def get_model_relationships(model):
    """Получает список отношений модели"""
    inspector = inspect(model)
    return set(r.key for r in inspector.relationships)


class TestBaseModelProperties:
    """Тесты для проверки базовых свойств всех моделей"""
    
    @pytest.mark.parametrize("model", [
        User, ActivityType, ActivitySubtype, NeedCategory, Need,
        Activity, ActivityEvaluation, ActivityNeed
    ])
    def test_model_inherits_from_base(self, model):
        """Проверяет, что все модели наследуются от Base"""
        assert issubclass(model, Base), f"Модель {model.__name__} должна наследоваться от Base"
    
    @pytest.mark.parametrize("model", [
        User, ActivityType, ActivitySubtype, NeedCategory, Need,
        Activity, ActivityEvaluation, ActivityNeed
    ])
    def test_model_has_base_columns(self, model):
        """Проверяет наличие базовых колонок во всех моделях"""
        columns = get_model_columns(model)
        assert "id" in columns, f"Модель {model.__name__} должна иметь колонку 'id'"
        assert "created_at" in columns, f"Модель {model.__name__} должна иметь колонку 'created_at'"
        assert "updated_at" in columns, f"Модель {model.__name__} должна иметь колонку 'updated_at'"
        assert "is_active" in columns, f"Модель {model.__name__} должна иметь колонку 'is_active'"


class TestUserModel:
    """Тесты для проверки модели User"""
    
    def test_user_columns(self):
        """Проверяет наличие всех необходимых колонок в модели User"""
        columns = get_model_columns(User)
        assert "email" in columns
        assert "hashed_password" in columns
        assert "first_name" in columns
        assert "last_name" in columns
        assert "is_superuser" in columns
    
    def test_user_relationships(self):
        """Проверяет наличие всех необходимых отношений в модели User"""
        relationships = get_model_relationships(User)
        assert "activities" in relationships
        assert "needs" in relationships


class TestActivityModels:
    """Тесты для проверки моделей, связанных с активностями"""
    
    def test_activity_type_columns(self):
        """Проверяет наличие всех необходимых колонок в модели ActivityType"""
        columns = get_model_columns(ActivityType)
        assert "name" in columns
        assert "description" in columns
        assert "color" in columns
        assert "icon" in columns
    
    def test_activity_type_relationships(self):
        """Проверяет наличие всех необходимых отношений в модели ActivityType"""
        relationships = get_model_relationships(ActivityType)
        assert "subtypes" in relationships
        assert "activities" in relationships
    
    def test_activity_subtype_columns(self):
        """Проверяет наличие всех необходимых колонок в модели ActivitySubtype"""
        columns = get_model_columns(ActivitySubtype)
        assert "name" in columns
        assert "description" in columns
        assert "activity_type_id" in columns
        assert "color" in columns
        assert "icon" in columns
    
    def test_activity_columns(self):
        """Проверяет наличие всех необходимых колонок в модели Activity"""
        columns = get_model_columns(Activity)
        assert "title" in columns
        assert "description" in columns
        assert "user_id" in columns
        assert "activity_type_id" in columns
        assert "activity_subtype_id" in columns
        assert "start_time" in columns
        assert "end_time" in columns
        assert "duration_minutes" in columns
        assert "is_completed" in columns
    
    def test_activity_relationships(self):
        """Проверяет наличие всех необходимых отношений в модели Activity"""
        relationships = get_model_relationships(Activity)
        assert "user" in relationships
        assert "activity_type" in relationships
        assert "activity_subtype" in relationships
        assert "evaluations" in relationships
        assert "activity_needs" in relationships


class TestNeedModels:
    """Тесты для проверки моделей, связанных с потребностями"""
    
    def test_need_category_columns(self):
        """Проверяет наличие всех необходимых колонок в модели NeedCategory"""
        columns = get_model_columns(NeedCategory)
        assert "name" in columns
        assert "description" in columns
        assert "color" in columns
        assert "icon" in columns
        assert "display_order" in columns
    
    def test_need_category_relationships(self):
        """Проверяет наличие всех необходимых отношений в модели NeedCategory"""
        relationships = get_model_relationships(NeedCategory)
        assert "needs" in relationships
    
    def test_need_columns(self):
        """Проверяет наличие всех необходимых колонок в модели Need"""
        columns = get_model_columns(Need)
        assert "name" in columns
        assert "description" in columns
        assert "category_id" in columns
        assert "user_id" in columns
        assert "is_custom" in columns
        assert "importance" in columns
    
    def test_need_relationships(self):
        """Проверяет наличие всех необходимых отношений в модели Need"""
        relationships = get_model_relationships(Need)
        assert "category" in relationships
        assert "user" in relationships
        assert "activity_needs" in relationships


class TestActivityNeedModel:
    """Тесты для проверки модели связи активностей и потребностей"""
    
    def test_activity_need_columns(self):
        """Проверяет наличие всех необходимых колонок в модели ActivityNeed"""
        columns = get_model_columns(ActivityNeed)
        assert "activity_id" in columns
        assert "need_id" in columns
        assert "strength" in columns
        assert "expected_impact" in columns
        assert "actual_impact" in columns
        assert "notes" in columns
    
    def test_activity_need_relationships(self):
        """Проверяет наличие всех необходимых отношений в модели ActivityNeed"""
        relationships = get_model_relationships(ActivityNeed)
        assert "activity" in relationships
        assert "need" in relationships