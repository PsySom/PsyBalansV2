from sqlalchemy import Column, String, Text, ForeignKey, Integer, DateTime, Float, Boolean, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import uuid
from datetime import datetime


class Exercise(BaseModel):
    """
    Модель упражнения.
    
    Специальный тип активности, представляющий структурированное упражнение
    с пошаговыми инструкциями, описанием сложности, целевыми состояниями и т.д.
    """
    __tablename__ = "exercises"
    
    activity_id = Column(UUID(as_uuid=True), ForeignKey("activities.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    instructions = Column(Text, nullable=False)  # Пошаговые инструкции
    duration_minutes = Column(Integer, nullable=False)  # Рекомендуемая продолжительность в минутах
    complexity = Column(Integer, default=3, nullable=False)  # Сложность от 1 до 5
    target_state = Column(String(50), nullable=True)  # Целевое состояние: релаксация, фокусировка и т.д.
    contraindications = Column(Text, nullable=True)  # Противопоказания
    benefits = Column(Text, nullable=True)  # Преимущества
    
    # Дополнительные параметры
    materials_needed = Column(Text, nullable=True)  # Необходимые материалы
    prerequisites = Column(Text, nullable=True)  # Предварительные условия
    category = Column(String(50), nullable=True)  # Категория упражнения
    tags = Column(JSONB, nullable=True)  # Теги для классификации
    
    # Валидационные ограничения
    __table_args__ = (
        CheckConstraint("complexity BETWEEN 1 AND 5", name="check_exercise_complexity_range"),
    )
    
    # Отношения
    activity = relationship("Activity", backref="exercise_info")
    progress = relationship("UserExerciseProgress", back_populates="exercise", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Exercise(name='{self.name}', complexity={self.complexity})>"


class Test(BaseModel):
    """
    Модель теста.
    
    Специальный тип активности, представляющий структурированный тест
    с вопросами, системой подсчета баллов и интерпретацией результатов.
    """
    __tablename__ = "tests"
    
    activity_id = Column(UUID(as_uuid=True), ForeignKey("activities.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    instructions = Column(Text, nullable=False)  # Инструкции
    questions_count = Column(Integer, nullable=False)  # Количество вопросов
    estimated_time_minutes = Column(Integer, nullable=False)  # Ориентировочное время прохождения
    scoring_algorithm = Column(String(100), nullable=True)  # Алгоритм подсчета результатов
    interpretation_guide = Column(Text, nullable=True)  # Руководство по интерпретации
    
    # Дополнительные параметры
    validity = Column(Text, nullable=True)  # Информация о валидности и надежности
    source = Column(String(255), nullable=True)  # Источник теста
    reference = Column(Text, nullable=True)  # Ссылки на исследования
    tags = Column(JSONB, nullable=True)  # Теги для классификации
    
    # Отношения
    activity = relationship("Activity", backref="test_info")
    
    def __repr__(self):
        return f"<Test(name='{self.name}', questions_count={self.questions_count})>"


class Practice(BaseModel):
    """
    Модель практики.
    
    Специальный тип активности, представляющий регулярную практику,
    которая обычно выполняется с определенной частотой для достижения результатов.
    """
    __tablename__ = "practices"
    
    activity_id = Column(UUID(as_uuid=True), ForeignKey("activities.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    frequency = Column(String(50), nullable=False)  # Рекомендуемая частота: 'daily', 'weekly', 'monthly' и т.д.
    duration_minutes = Column(Integer, nullable=False)  # Рекомендуемая продолжительность в минутах
    level = Column(String(50), default='beginner', nullable=False)  # Уровень: 'beginner', 'intermediate', 'advanced'
    category = Column(String(50), nullable=True)  # Категория практики
    benefits = Column(Text, nullable=True)  # Преимущества
    
    # Дополнительные параметры
    commitment_period = Column(String(50), nullable=True)  # Рекомендуемый период приверженности (например, '30 days')
    milestones = Column(JSONB, nullable=True)  # Вехи прогресса
    tags = Column(JSONB, nullable=True)  # Теги для классификации
    
    # Валидационные ограничения
    __table_args__ = (
        CheckConstraint("level IN ('beginner', 'intermediate', 'advanced')", name="check_practice_level"),
    )
    
    # Отношения
    activity = relationship("Activity", backref="practice_info")
    
    def __repr__(self):
        return f"<Practice(name='{self.name}', frequency='{self.frequency}', level='{self.level}')>"


class UserExerciseProgress(BaseModel):
    """
    Модель прогресса пользователя в упражнениях.
    
    Отслеживает прогресс пользователя в выполнении упражнений,
    включая количество выполнений, эффективность и заметки.
    """
    __tablename__ = "user_exercise_progress"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    exercise_id = Column(UUID(as_uuid=True), ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False)
    completed_count = Column(Integer, default=0, nullable=False)  # Количество выполнений
    last_completed = Column(DateTime(timezone=True), nullable=True)  # Последнее выполнение
    effectiveness_rating = Column(Float, nullable=True)  # Оценка эффективности (от 0 до 5)
    notes = Column(Text, nullable=True)  # Заметки пользователя
    is_favorite = Column(Boolean, default=False, nullable=False)  # Добавлено в избранное
    
    # Дополнительные параметры
    average_duration_minutes = Column(Integer, nullable=True)  # Средняя продолжительность выполнения
    difficulty_rating = Column(Float, nullable=True)  # Оценка сложности (от 1 до 5)
    customizations = Column(JSONB, nullable=True)  # Персонализированные настройки
    tags = Column(JSONB, nullable=True)  # Пользовательские теги
    
    # Валидационные ограничения
    __table_args__ = (
        UniqueConstraint("user_id", "exercise_id", name="uix_user_exercise"),
        CheckConstraint("effectiveness_rating BETWEEN 0 AND 5 OR effectiveness_rating IS NULL", 
                       name="check_effectiveness_rating_range"),
        CheckConstraint("difficulty_rating BETWEEN 1 AND 5 OR difficulty_rating IS NULL", 
                       name="check_difficulty_rating_range"),
    )
    
    # Отношения
    user = relationship("User", backref="exercise_progress")
    exercise = relationship("Exercise", back_populates="progress")
    
    def __repr__(self):
        return f"<UserExerciseProgress(user_id='{self.user_id}', exercise='{self.exercise_id}', completed={self.completed_count})>"