import pytest
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
import uuid

from app.models import Exercise, Test, Practice, UserExerciseProgress, Activity, User
from app.core.database.postgresql import get_db


@pytest.fixture
def test_user(get_db):
    """Создает тестового пользователя"""
    db = next(get_db())
    user = User(
        email="test@example.com",
        hashed_password="hashed_password",
        first_name="Test",
        last_name="User"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    yield user
    db.delete(user)
    db.commit()


@pytest.fixture
def test_activity(get_db, test_user):
    """Создает тестовую активность"""
    db = next(get_db())
    now = datetime.now()
    activity = Activity(
        title="Test Activity",
        description="Test Description",
        user_id=test_user.id,
        start_time=now,
        end_time=now + timedelta(hours=1),
        duration_minutes=60,
        priority=3,
        energy_required=2
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    yield activity
    db.delete(activity)
    db.commit()


class TestExerciseModels:
    
    def test_create_exercise(self, get_db, test_activity):
        """Тест создания упражнения"""
        db = next(get_db())
        exercise = Exercise(
            activity_id=test_activity.id,
            name="Медитация осознанности",
            description="Базовая практика для развития внимательности",
            instructions="1. Сядьте удобно\n2. Закройте глаза\n3. Сосредоточьтесь на дыхании",
            duration_minutes=15,
            complexity=2,
            target_state="релаксация",
            benefits="Снижение стресса, улучшение концентрации"
        )
        
        db.add(exercise)
        db.commit()
        db.refresh(exercise)
        
        assert exercise.id is not None
        assert exercise.name == "Медитация осознанности"
        assert exercise.complexity == 2
        assert exercise.target_state == "релаксация"
        
        db.delete(exercise)
        db.commit()
    
    def test_create_test(self, get_db, test_activity):
        """Тест создания психологического теста"""
        db = next(get_db())
        psych_test = Test(
            activity_id=test_activity.id,
            name="Тест на уровень тревожности",
            description="Определяет текущий уровень тревожности",
            instructions="Ответьте на все вопросы честно",
            questions_count=20,
            estimated_time_minutes=10,
            scoring_algorithm="sum",
            interpretation_guide="0-20: низкий уровень\n21-40: средний уровень\n41-60: высокий уровень"
        )
        
        db.add(psych_test)
        db.commit()
        db.refresh(psych_test)
        
        assert psych_test.id is not None
        assert psych_test.name == "Тест на уровень тревожности"
        assert psych_test.questions_count == 20
        
        db.delete(psych_test)
        db.commit()
    
    def test_create_practice(self, get_db, test_activity):
        """Тест создания практики"""
        db = next(get_db())
        practice = Practice(
            activity_id=test_activity.id,
            name="Ежедневный журнал благодарности",
            description="Практика записи того, за что вы благодарны",
            frequency="daily",
            duration_minutes=10,
            level="beginner",
            category="благополучие",
            benefits="Улучшение настроения, развитие позитивного мышления"
        )
        
        db.add(practice)
        db.commit()
        db.refresh(practice)
        
        assert practice.id is not None
        assert practice.name == "Ежедневный журнал благодарности"
        assert practice.frequency == "daily"
        assert practice.level == "beginner"
        
        db.delete(practice)
        db.commit()
    
    def test_user_exercise_progress(self, get_db, test_user, test_activity):
        """Тест отслеживания прогресса пользователя по упражнениям"""
        db = next(get_db())
        
        # Создаем упражнение
        exercise = Exercise(
            activity_id=test_activity.id,
            name="Медитация осознанности",
            description="Базовая практика для развития внимательности",
            instructions="1. Сядьте удобно\n2. Закройте глаза\n3. Сосредоточьтесь на дыхании",
            duration_minutes=15,
            complexity=2,
            target_state="релаксация",
            benefits="Снижение стресса, улучшение концентрации"
        )
        
        db.add(exercise)
        db.commit()
        db.refresh(exercise)
        
        # Создаем запись о прогрессе
        progress = UserExerciseProgress(
            user_id=test_user.id,
            exercise_id=exercise.id,
            completed_count=5,
            last_completed=datetime.now(),
            effectiveness_rating=4.5,
            notes="Очень помогает расслабиться",
            is_favorite=True
        )
        
        db.add(progress)
        db.commit()
        db.refresh(progress)
        
        assert progress.id is not None
        assert progress.completed_count == 5
        assert progress.effectiveness_rating == 4.5
        assert progress.is_favorite is True
        
        # Проверяем связи
        assert progress.user.id == test_user.id
        assert progress.exercise.id == exercise.id
        
        db.delete(progress)
        db.delete(exercise)
        db.commit()
    
    def test_invalid_complexity(self, get_db, test_activity):
        """Тест валидации ограничений на сложность упражнения"""
        db = next(get_db())
        
        # Создаем упражнение с недопустимой сложностью
        exercise = Exercise(
            activity_id=test_activity.id,
            name="Недопустимое упражнение",
            description="Тест на валидацию",
            instructions="Инструкции",
            duration_minutes=15,
            complexity=6,  # Должно быть от 1 до 5
            target_state="тест"
        )
        
        db.add(exercise)
        
        # Должно вызвать ошибку из-за ограничения CHECK
        with pytest.raises(IntegrityError):
            db.commit()
        
        db.rollback()