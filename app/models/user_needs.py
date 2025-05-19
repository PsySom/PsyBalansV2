from sqlalchemy import Column, String, Text, ForeignKey, Integer, DateTime, Float, Boolean, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import uuid
from datetime import datetime, timedelta


class UserNeed(BaseModel):
    """
    Модель потребности пользователя.
    
    Расширяет базовую модель Need, связывая конкретного пользователя с его потребностями.
    Позволяет настраивать и персонализировать потребности.
    """
    __tablename__ = "user_needs"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    need_id = Column(UUID(as_uuid=True), ForeignKey("needs.id", ondelete="CASCADE"), nullable=False)
    
    # Индивидуальные настройки потребности
    importance = Column(Float, default=0.6, nullable=False)  # Важность для пользователя (0.0-1.0)
    target_satisfaction = Column(Float, default=3.0, nullable=False)  # Целевой уровень удовлетворенности (-5 до 5)
    current_satisfaction = Column(Float, default=0.0, nullable=False)  # Текущий уровень удовлетворенности (-5 до 5)
    is_favorite = Column(Boolean, default=False, nullable=False)  # Флаг "избранной" потребности
    
    # Персонализированные параметры
    custom_name = Column(String(100), nullable=True)  # Пользовательское название
    custom_description = Column(Text, nullable=True)  # Пользовательское описание
    custom_color = Column(String(7), nullable=True)  # Пользовательский цвет
    custom_icon = Column(String(50), nullable=True)  # Пользовательская иконка
    
    # Настройки и дополнительные параметры
    settings = Column(JSONB, nullable=True)  # Настройки в формате JSON
    notes = Column(Text, nullable=True)  # Заметки пользователя
    
    # Валидационные ограничения
    __table_args__ = (
        CheckConstraint("importance BETWEEN 0.0 AND 1.0", name="check_user_need_importance_range"),
        CheckConstraint("target_satisfaction BETWEEN -5.0 AND 5.0", name="check_user_need_target_range"),
        CheckConstraint("current_satisfaction BETWEEN -5.0 AND 5.0", name="check_user_need_current_range"),
    )
    
    # Отношения
    user = relationship("User", backref="user_needs")
    need = relationship("Need", backref="user_needs")
    history = relationship("UserNeedHistory", back_populates="user_need", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<UserNeed(user_id='{self.user_id}', need_id='{self.need_id}', satisfaction={self.current_satisfaction}%)>"
    
    @property
    def name(self):
        """Возвращает название потребности (пользовательское или оригинальное)"""
        return self.custom_name if self.custom_name else self.need.name
    
    @property
    def description(self):
        """Возвращает описание потребности (пользовательское или оригинальное)"""
        return self.custom_description if self.custom_description else self.need.description
    
    @property
    def color(self):
        """Возвращает цвет потребности (пользовательский или оригинальный)"""
        return self.custom_color if self.custom_color else self.need.category.color
    
    @property
    def icon(self):
        """Возвращает иконку потребности (пользовательскую или оригинальную)"""
        return self.custom_icon if self.custom_icon else self.need.category.icon
    
    def update_satisfaction(self, new_value, note=None, context=None):
        """Обновляет текущий уровень удовлетворенности и создает запись в истории"""
        old_value = self.current_satisfaction
        self.current_satisfaction = max(-5.0, min(5.0, new_value))  # Ограничиваем значение в диапазоне -5 до 5
        
        # Создаем запись в истории
        history_entry = UserNeedHistory(
            user_need_id=self.id,
            user_id=self.user_id,
            need_id=self.need_id,
            satisfaction_level=self.current_satisfaction,
            previous_value=old_value,
            change_value=self.current_satisfaction - old_value,
            note=note,
            context=context
        )
        
        return history_entry


class UserNeedHistory(BaseModel):
    """
    Модель истории потребностей пользователя.
    
    Отслеживает изменения в уровне удовлетворенности потребностей пользователя,
    позволяя анализировать динамику и выявлять тренды.
    """
    __tablename__ = "user_need_history"
    
    user_need_id = Column(UUID(as_uuid=True), ForeignKey("user_needs.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    need_id = Column(UUID(as_uuid=True), ForeignKey("needs.id", ondelete="CASCADE"), nullable=False)
    
    # Значения и изменения
    satisfaction_level = Column(Float, nullable=False)  # Уровень удовлетворенности в момент записи (-5 до 5)
    previous_value = Column(Float, nullable=True)  # Предыдущее значение
    change_value = Column(Float, nullable=True)  # Разница между текущим и предыдущим значением
    
    # Связь с активностью (опционально)
    activity_id = Column(UUID(as_uuid=True), ForeignKey("activities.id", ondelete="SET NULL"), nullable=True)
    activity_schedule_id = Column(UUID(as_uuid=True), ForeignKey("activity_schedules.id", ondelete="SET NULL"), nullable=True)
    
    # Временные параметры и контекст
    timestamp = Column(DateTime(timezone=True), default=datetime.now, nullable=False)  # Время записи
    context = Column(String(50), nullable=True)  # Контекст измерения (morning_check, evening_review, etc.)
    note = Column(Text, nullable=True)  # Заметка о причине изменения
    
    # Отношения
    user_need = relationship("UserNeed", back_populates="history")
    user = relationship("User", backref="need_history")
    need = relationship("Need", backref="history")
    activity = relationship("Activity", backref="need_history")
    schedule = relationship("ActivitySchedule", backref="need_history")
    
    def __repr__(self):
        return f"<UserNeedHistory(user_id='{self.user_id}', need_id='{self.need_id}', change={self.change_value})>"


class NeedFulfillmentPlan(BaseModel):
    """
    Модель плана удовлетворения потребностей.
    
    Позволяет пользователю создавать планы и цели по удовлетворению потребностей.
    """
    __tablename__ = "need_fulfillment_plans"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Временные параметры
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    
    # Статус
    status = Column(String(20), default="active", nullable=False)  # active, completed, cancelled, paused
    
    # Настройки
    settings = Column(JSONB, nullable=True)  # Настройки плана
    
    # Валидационные ограничения
    __table_args__ = (
        CheckConstraint("end_date > start_date", name="check_plan_end_date_after_start_date"),
        CheckConstraint("status IN ('active', 'completed', 'cancelled', 'paused')", name="check_plan_status"),
    )
    
    # Отношения
    user = relationship("User", backref="need_plans")
    objectives = relationship("NeedFulfillmentObjective", back_populates="plan", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<NeedFulfillmentPlan(name='{self.name}', user_id='{self.user_id}')>"


class NeedFulfillmentObjective(BaseModel):
    """
    Модель цели в плане удовлетворения потребностей.
    
    Конкретная цель по удовлетворению определенной потребности в рамках плана.
    """
    __tablename__ = "need_fulfillment_objectives"
    
    plan_id = Column(UUID(as_uuid=True), ForeignKey("need_fulfillment_plans.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    need_id = Column(UUID(as_uuid=True), ForeignKey("needs.id", ondelete="CASCADE"), nullable=False)
    user_need_id = Column(UUID(as_uuid=True), ForeignKey("user_needs.id", ondelete="CASCADE"), nullable=False)
    
    # Параметры цели
    target_value = Column(Integer, nullable=False)  # Целевое значение удовлетворенности (0-100%)
    current_value = Column(Integer, nullable=False)  # Текущее значение
    starting_value = Column(Integer, nullable=False)  # Начальное значение
    
    # Статус
    status = Column(String(20), default="in_progress", nullable=False)  # not_started, in_progress, completed, failed
    completion_date = Column(DateTime(timezone=True), nullable=True)  # Дата достижения цели
    
    # Дополнительные параметры
    priority = Column(Integer, default=3, nullable=False)  # Приоритет (1-5)
    notes = Column(Text, nullable=True)  # Заметки
    
    # Валидационные ограничения
    __table_args__ = (
        CheckConstraint("target_value BETWEEN 0 AND 100", name="check_objective_target_range"),
        CheckConstraint("current_value BETWEEN 0 AND 100", name="check_objective_current_range"),
        CheckConstraint("starting_value BETWEEN 0 AND 100", name="check_objective_starting_range"),
        CheckConstraint("priority BETWEEN 1 AND 5", name="check_objective_priority_range"),
        CheckConstraint("status IN ('not_started', 'in_progress', 'completed', 'failed')", name="check_objective_status"),
    )
    
    # Отношения
    plan = relationship("NeedFulfillmentPlan", back_populates="objectives")
    user = relationship("User", backref="need_objectives")
    need = relationship("Need", backref="objectives")
    user_need = relationship("UserNeed", backref="objectives")
    
    def __repr__(self):
        return f"<NeedFulfillmentObjective(need='{self.need_id}', target_value={self.target_value}%)>"
    
    @property
    def progress(self):
        """Рассчитывает процент прогресса в достижении цели"""
        if self.target_value == self.starting_value:
            return 100 if self.current_value == self.target_value else 0
        
        total_change = self.target_value - self.starting_value
        current_change = self.current_value - self.starting_value
        
        if total_change == 0:
            return 100  # Если цель и начальное значение совпадают, прогресс 100%
        
        progress = (current_change / total_change) * 100
        return max(0, min(100, progress))  # Ограничиваем значение в диапазоне 0-100