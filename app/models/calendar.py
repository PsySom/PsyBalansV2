from sqlalchemy import Column, String, Text, ForeignKey, Integer, DateTime, JSON, Boolean, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import uuid
from datetime import datetime, timedelta


class UserCalendar(BaseModel):
    """
    Модель календаря пользователя.
    
    Представляет собой контейнер для планирования активностей пользователя.
    Пользователь может иметь несколько календарей для разных сфер жизни.
    """
    __tablename__ = "user_calendars"
    
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    color = Column(String(20), nullable=True)  # HEX-код цвета
    icon = Column(String(50), nullable=True)  # Иконка календаря
    is_default = Column(Boolean, default=False, nullable=False)  # Флаг календаря по умолчанию
    is_primary = Column(Boolean, default=False, nullable=False)  # Флаг основного календаря
    is_visible = Column(Boolean, default=True, nullable=False)  # Флаг видимости календаря
    is_public = Column(Boolean, default=False, nullable=False)  # Флаг публичного календаря
    is_shared = Column(Boolean, default=False, nullable=False)  # Флаг общего календаря
    
    # Синхронизация с внешними календарями
    external_id = Column(String(255), nullable=True)  # ID календаря в внешней системе
    external_source = Column(String(50), nullable=True)  # Источник внешнего календаря
    external_url = Column(String(255), nullable=True)  # URL внешнего календаря
    sync_status = Column(String(20), nullable=True)  # Статус синхронизации
    last_synced = Column(DateTime, nullable=True)  # Время последней синхронизации
    
    timezone = Column(String(50), nullable=True, default="UTC")
    display_order = Column(Integer, default=100, nullable=False)
    settings = Column(JSONB, nullable=True)  # Настройки календаря в формате JSON
    calendar_metadata = Column(JSONB, nullable=True)  # Метаданные календаря
    
    # Отношения
    user = relationship("User", backref="calendars")
    schedules = relationship("ActivitySchedule", back_populates="calendar", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<UserCalendar(name='{self.name}', user_id='{self.user_id}')>"


class ActivitySchedule(BaseModel):
    """
    Модель расписания активностей.
    
    Представляет собой конкретный экземпляр активности в календаре, который
    может быть создан пользователем или сгенерирован системой на основе шаблона.
    """
    __tablename__ = "activity_schedules"
    
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    calendar_id = Column(UUID(as_uuid=True), ForeignKey("user_calendars.id", ondelete="CASCADE"), nullable=True)
    activity_id = Column(UUID(as_uuid=True), ForeignKey("activities.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Временные параметры
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, nullable=False)  # Продолжительность в минутах
    all_day = Column(Boolean, default=False, nullable=False)  # Флаг "весь день"
    
    # Статус выполнения
    status = Column(String(20), default="scheduled", nullable=False)  # scheduled, in_progress, completed, cancelled, postponed
    completion_time = Column(DateTime(timezone=True), nullable=True)  # Время фактического завершения
    completion_percentage = Column(Integer, nullable=True)  # Процент выполнения
    
    # Повторение
    recurrence_rule = Column(String(255), nullable=True)  # iCalendar RRULE формат для повторяющихся событий
    recurrence_exception_dates = Column(JSONB, nullable=True)  # Исключения из повторения
    recurrence_id = Column(UUID(as_uuid=True), ForeignKey("activity_schedules.id"), nullable=True)  # ID оригинального события для исключений
    
    # Для обратной совместимости
    is_recurring = Column(Boolean, default=False, nullable=False)  # Флаг повторяющегося события
    recurrence_pattern = Column(JSONB, nullable=True)  # Паттерн повторения (ежедневно, еженедельно и т.д.)
    recurrence_parent_id = Column(UUID(as_uuid=True), ForeignKey("activity_schedules.id"), nullable=True)  # Родительское событие
    
    # Дополнительные параметры
    priority = Column(Integer, default=3, nullable=False)  # Приоритет (1-5)
    is_flexible = Column(Boolean, default=False, nullable=False)  # Можно ли перемещать/менять время
    location = Column(String(255), nullable=True)  # Место проведения
    color = Column(String(20), nullable=True)  # Цвет события
    
    # Буферное время
    buffer_before = Column(Integer, nullable=True)  # Буферное время до активности в минутах
    buffer_after = Column(Integer, nullable=True)  # Буферное время после активности в минутах
    
    # Энергия и настроение
    energy_required = Column(Integer, nullable=True)  # Ожидаемые затраты энергии (1-10)
    preferred_energy_level = Column(Integer, nullable=True)  # Предпочтительный уровень энергии (1-10)
    preferred_mood_level = Column(Integer, nullable=True)  # Предпочтительный уровень настроения (1-10)
    
    # Напоминания
    reminder_times = Column(JSONB, nullable=True)  # Минуты до начала для оповещений
    
    # Связь с целями
    linked_plan_objective_id = Column(UUID(as_uuid=True), ForeignKey("need_fulfillment_objectives.id"), nullable=True)
    
    # Внешние системы
    external_id = Column(String(255), nullable=True)  # ID во внешней системе (Google Calendar и т.д.)
    external_source = Column(String(50), nullable=True)  # Источник внешней системы
    
    # Прочее
    notes = Column(Text, nullable=True)  # Заметки
    reminders = Column(JSONB, nullable=True)  # Настройки напоминаний
    tags = Column(JSONB, nullable=True)  # Теги
    settings = Column(JSONB, nullable=True)  # Настройки
    schedule_metadata = Column(JSONB, nullable=True)  # Метаданные
    
    # Валидационные ограничения
    __table_args__ = (
        CheckConstraint("end_time > start_time", name="check_schedule_end_time_after_start_time"),
        CheckConstraint("priority BETWEEN 1 AND 5", name="check_schedule_priority_range"),
        CheckConstraint("status IN ('scheduled', 'in_progress', 'completed', 'cancelled', 'postponed')", name="check_schedule_status"),
    )
    
    # Отношения
    calendar = relationship("UserCalendar", back_populates="schedules")
    activity = relationship("Activity", backref="schedules")
    user = relationship("User", backref="schedules")
    recurring_schedules = relationship("ActivitySchedule", 
                                      backref="parent_schedule",
                                      remote_side=[id],
                                      cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ActivitySchedule(title='{self.title}', start_time='{self.start_time}')>"
    
    @property
    def is_overdue(self):
        """Проверяет, просрочено ли событие расписания"""
        return self.status == "scheduled" and self.end_time < datetime.now()
    
    @property
    def is_in_progress(self):
        """Проверяет, выполняется ли событие расписания в текущий момент"""
        now = datetime.now()
        return (self.status == "scheduled" or self.status == "in_progress") and self.start_time <= now <= self.end_time
    
    def calculate_duration(self):
        """Рассчитывает продолжительность события в минутах"""
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds() / 60
            return int(duration)
        return 0
    
    def update_duration(self):
        """Обновляет продолжительность на основе времени начала и окончания"""
        self.duration_minutes = self.calculate_duration()
    
    def mark_as_completed(self, completion_time=None):
        """Отмечает событие как завершенное"""
        self.status = "completed"
        self.completion_time = completion_time or datetime.now()
    
    def mark_as_in_progress(self):
        """Отмечает событие как выполняемое"""
        self.status = "in_progress"
    
    def mark_as_cancelled(self):
        """Отмечает событие как отмененное"""
        self.status = "cancelled"
    
    def postpone(self, new_start_time, new_end_time=None):
        """Откладывает событие на другое время"""
        self.status = "postponed"
        self.start_time = new_start_time
        if new_end_time:
            self.end_time = new_end_time
        else:
            duration = timedelta(minutes=self.duration_minutes)
            self.end_time = new_start_time + duration
        self.update_duration()