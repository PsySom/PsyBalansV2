from sqlalchemy import Column, String, Text, ForeignKey, Integer, DateTime, Float, Boolean, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import uuid
from datetime import datetime, timedelta


class Activity(BaseModel):
    """Модель активности пользователя
    
    Основная модель для представления действий, которые пользователь планирует
    или выполняет для удовлетворения своих потребностей.
    """
    __tablename__ = "activities"
    
    # Основные поля
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Классификация активности
    activity_type_id = Column(UUID(as_uuid=True), ForeignKey("activity_types.id"), nullable=True)
    activity_subtype_id = Column(UUID(as_uuid=True), ForeignKey("activity_subtypes.id"), nullable=True)
    
    # Временные параметры активности
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, nullable=False)  # Продолжительность в минутах
    
    # Статус выполнения
    is_completed = Column(Boolean, default=False, nullable=False)
    completion_time = Column(DateTime(timezone=True), nullable=True)  # Время фактического завершения
    
    # Повторение активности
    is_recurring = Column(Boolean, default=False, nullable=False)  # Флаг повторяющейся активности
    recurrence_pattern = Column(JSONB, nullable=True)  # Паттерн повторения (ежедневно, еженедельно и т.д.)
    parent_activity_id = Column(UUID(as_uuid=True), ForeignKey("activities.id"), nullable=True)  # Родительская активность для повторяющихся
    
    # Дополнительные параметры
    priority = Column(Integer, default=2, nullable=False)  # Приоритет активности (1-5)
    energy_required = Column(Integer, default=3, nullable=False)  # Требуемый уровень энергии (1-5)
    color = Column(String(7), nullable=True)  # HEX-код цвета
    location = Column(String(255), nullable=True)  # Место проведения активности
    tags = Column(JSONB, nullable=True)  # Произвольные теги для классификации
    
    # Валидационные ограничения
    __table_args__ = (
        CheckConstraint("end_time > start_time", name="check_end_time_after_start_time"),  # Конец должен быть позже начала
        CheckConstraint("priority BETWEEN 1 AND 5", name="check_priority_range"),  # Проверка диапазона приоритета
        CheckConstraint("energy_required BETWEEN 1 AND 5", name="check_energy_range"),  # Проверка диапазона энергии
    )
    
    # Отношения
    user = relationship("User", back_populates="activities")
    activity_type = relationship("ActivityType", back_populates="activities")
    activity_subtype = relationship("ActivitySubtype", back_populates="activities")
    recurring_activities = relationship("Activity", 
                                        backref="parent_activity", 
                                        remote_side=[id],
                                        cascade="all, delete-orphan")
    evaluations = relationship("ActivityEvaluation", back_populates="activity", cascade="all, delete-orphan")
    activity_needs = relationship("ActivityNeed", back_populates="activity", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Activity(title='{self.title}', user_id='{self.user_id}')>"
    
    @property
    def is_overdue(self):
        """Проверяет, просрочена ли активность"""
        return not self.is_completed and self.end_time < datetime.now()
    
    @property
    def is_in_progress(self):
        """Проверяет, выполняется ли активность в текущий момент"""
        now = datetime.now()
        return not self.is_completed and self.start_time <= now <= self.end_time
    
    def calculate_duration(self):
        """Рассчитывает продолжительность активности в минутах"""
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds() / 60
            return int(duration)
        return 0
    
    def update_duration(self):
        """Обновляет продолжительность на основе времени начала и окончания"""
        self.duration_minutes = self.calculate_duration()


class ActivityEvaluation(BaseModel):
    """Модель оценки выполненной активности
    
    Позволяет пользователю оценить различные аспекты активности после её выполнения,
    что помогает анализировать эффективность активностей для удовлетворения потребностей.
    """
    __tablename__ = "activity_evaluations"
    
    activity_id = Column(UUID(as_uuid=True), ForeignKey("activities.id", ondelete="CASCADE"), nullable=False)
    
    # Оценки
    satisfaction_score = Column(Integer, nullable=True)  # Общая удовлетворенность (1-10)
    enjoyment_score = Column(Integer, nullable=True)  # Насколько понравилось (1-10)
    difficulty_score = Column(Integer, nullable=True)  # Сложность (1-10)
    energy_change = Column(Integer, nullable=True)  # Изменение энергии (-5 до +5)
    mood_change = Column(Integer, nullable=True)  # Изменение настроения (-5 до +5)
    stress_level = Column(Integer, nullable=True)  # Уровень стресса (1-10)
    
    notes = Column(Text, nullable=True)  # Заметки пользователя
    tags = Column(JSONB, nullable=True)  # Теги, связанные с оценкой
    
    # Валидационные ограничения
    __table_args__ = (
        CheckConstraint("satisfaction_score BETWEEN 1 AND 10", name="check_satisfaction_range"),
        CheckConstraint("enjoyment_score BETWEEN 1 AND 10", name="check_enjoyment_range"),
        CheckConstraint("difficulty_score BETWEEN 1 AND 10", name="check_difficulty_range"),
        CheckConstraint("energy_change BETWEEN -5 AND 5", name="check_energy_change_range"),
        CheckConstraint("mood_change BETWEEN -5 AND 5", name="check_mood_change_range"),
        CheckConstraint("stress_level BETWEEN 1 AND 10", name="check_stress_range"),
    )
    
    # Отношения
    activity = relationship("Activity", back_populates="evaluations")
    
    def __repr__(self):
        return f"<ActivityEvaluation(activity_id='{self.activity_id}', satisfaction={self.satisfaction_score})>"


class ActivityNeed(BaseModel):
    """Модель связи между активностью и потребностью
    
    Представляет связь многие-ко-многим между активностями и потребностями,
    с дополнительными атрибутами, описывающими силу этой связи и её характеристики.
    """
    __tablename__ = "activity_needs"
    
    activity_id = Column(UUID(as_uuid=True), ForeignKey("activities.id", ondelete="CASCADE"), nullable=False)
    need_id = Column(UUID(as_uuid=True), ForeignKey("needs.id", ondelete="CASCADE"), nullable=False)
    
    # Сила связи между активностью и потребностью
    strength = Column(Integer, default=3, nullable=False)  # Шкала от 1 до 5, где 5 - сильная связь
    
    # Ожидаемое влияние активности на потребность
    expected_impact = Column(Integer, default=3, nullable=False)  # От 1 до 5, где 5 - наибольшее влияние
    
    # Фактический результат (заполняется после выполнения активности)
    actual_impact = Column(Integer, nullable=True)  # От 1 до 5, где 5 - наибольшее влияние
    
    # Заметки к связи
    notes = Column(Text, nullable=True)
    
    # Валидационные ограничения
    __table_args__ = (
        # Уникальное ограничение: активность-потребность (уникальная пара)
        UniqueConstraint("activity_id", "need_id", name="uix_activity_need"),
        
        # Проверки диапазонов
        CheckConstraint("strength BETWEEN 1 AND 5", name="check_strength_range"),
        CheckConstraint("expected_impact BETWEEN 1 AND 5", name="check_expected_impact_range"),
        CheckConstraint("actual_impact BETWEEN 1 AND 5 OR actual_impact IS NULL", name="check_actual_impact_range"),
    )
    
    # Отношения
    activity = relationship("Activity", back_populates="activity_needs")
    need = relationship("Need", back_populates="activity_needs")
    
    def __repr__(self):
        return f"<ActivityNeed(activity='{self.activity_id}', need='{self.need_id}', strength={self.strength})>"