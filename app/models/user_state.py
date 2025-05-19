from sqlalchemy import Column, String, Text, ForeignKey, Integer, DateTime, Float, JSON, CheckConstraint, Date, Boolean, Table
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import uuid
from datetime import datetime, timedelta


# Таблица для связи шкал с категориями
scale_category_association = Table(
    "scale_category_association",
    BaseModel.metadata,
    Column("scale_id", UUID(as_uuid=True), ForeignKey("observation_scales.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", UUID(as_uuid=True), ForeignKey("scale_categories.id", ondelete="CASCADE"), primary_key=True)
)


class ScaleCategory(BaseModel):
    """
    Модель категории шкал самонаблюдения.
    
    Позволяет группировать шкалы по категориям (например, эмоциональные, физические, когнитивные и т.д.).
    """
    __tablename__ = "scale_categories"
    
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)
    color = Column(String(20), nullable=True)
    order = Column(Integer, default=0, nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)  # Системная категория или пользовательская
    
    # Отношения
    scales = relationship("ObservationScale", secondary=scale_category_association, back_populates="categories")


class ObservationScale(BaseModel):
    """
    Модель шкалы самонаблюдения.
    
    Определяет параметры шкалы для оценки различных аспектов состояния пользователя.
    """
    __tablename__ = "observation_scales"
    
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)
    color = Column(String(20), nullable=True)
    min_value = Column(Float, nullable=False)
    max_value = Column(Float, nullable=False)
    step = Column(Float, default=1.0, nullable=False)  # Шаг шкалы
    default_value = Column(Float, nullable=True)
    unit = Column(String(20), nullable=True)  # Единица измерения (если применимо)
    
    # Настройки отображения
    display_type = Column(String(20), default="slider", nullable=False)  # slider, buttons, input, stars, etc.
    labels = Column(JSONB, nullable=True)  # Метки для различных значений шкалы
    
    # Настройки шкалы
    is_inverted = Column(Boolean, default=False, nullable=False)  # Инвертированная шкала (выше=хуже)
    is_required = Column(Boolean, default=False, nullable=False)  # Обязательно ли заполнение
    is_system = Column(Boolean, default=False, nullable=False)  # Системная или пользовательская шкала
    is_active = Column(Boolean, default=True, nullable=False)  # Активна ли шкала
    
    # Настройки уведомлений
    alert_threshold_min = Column(Float, nullable=True)  # Минимальный порог для оповещений
    alert_threshold_max = Column(Float, nullable=True)  # Максимальный порог для оповещений
    
    # Настройки графиков
    chart_color = Column(String(20), nullable=True)  # Цвет линии на графике
    chart_type = Column(String(20), default="line", nullable=False)  # Тип графика: line, bar, etc
    
    # Связи с другими моделями
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Отношения
    categories = relationship("ScaleCategory", secondary=scale_category_association, back_populates="scales")
    ratings = relationship("ScaleRating", back_populates="scale", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[creator_id])


class ScaleRating(BaseModel):
    """
    Модель оценки по шкале самонаблюдения.
    
    Хранит оценки пользователя по различным шкалам с привязкой к времени.
    """
    __tablename__ = "scale_ratings"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    scale_id = Column(UUID(as_uuid=True), ForeignKey("observation_scales.id", ondelete="CASCADE"), nullable=False)
    value = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=datetime.now, nullable=False)
    
    # Связь с активностью (опционально)
    activity_id = Column(UUID(as_uuid=True), ForeignKey("activities.id", ondelete="SET NULL"), nullable=True)
    activity_schedule_id = Column(UUID(as_uuid=True), ForeignKey("activity_schedules.id", ondelete="SET NULL"), nullable=True)
    
    # Дополнительные параметры
    notes = Column(Text, nullable=True)
    context = Column(JSONB, nullable=True)  # Контекст оценки (место, занятие и т.д.)
    
    # Отношения
    user = relationship("User", backref="scale_ratings")
    scale = relationship("ObservationScale", back_populates="ratings")
    activity = relationship("Activity", backref="scale_ratings")
    activity_schedule = relationship("ActivitySchedule", backref="scale_ratings")


class UserState(BaseModel):
    """
    Модель состояния пользователя.
    
    Агрегирует различные показатели состояния пользователя в определенный момент времени,
    позволяя отслеживать динамику благополучия и эффективность активностей.
    """
    __tablename__ = "user_states"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=datetime.now, nullable=False)
    date = Column(Date, default=datetime.now().date, nullable=False)
    entry_type = Column(String(20), default="manual", nullable=False)  # manual, scheduled, inferred
    
    # Основные показатели состояния
    mood_level = Column(Integer, nullable=True)  # Уровень настроения (-10 до +10)
    mood_score = Column(Float, nullable=True)  # Оценка настроения (-10 до 10) - для обратной совместимости
    energy_level = Column(Integer, nullable=True)  # Уровень энергии (-10 до 10)
    stress_level = Column(Integer, nullable=True)  # Уровень стресса (0 до 10)
    anxiety_level = Column(Integer, nullable=True)  # Уровень тревожности (0 до 10)
    focus_level = Column(Integer, nullable=True)  # Уровень концентрации (0-100)
    motivation_level = Column(Integer, nullable=True)  # Уровень мотивации (0-100)
    physical_well_being = Column(Integer, nullable=True)  # Физическое состояние (0-10)
    
    # Контекст
    location = Column(String(255), nullable=True)  # Местоположение
    activity_context = Column(String(100), nullable=True)  # Чем занимался в момент оценки
    social_context = Column(String(100), nullable=True)  # С кем был в момент оценки
    
    # Эмоции и симптомы
    emotions = Column(ARRAY(String), nullable=True)  # Испытываемые эмоции
    physical_symptoms = Column(ARRAY(String), nullable=True)  # Физические симптомы
    
    # Тип периода
    period_type = Column(String(20), default="instant", nullable=False)  # Тип периода: instant, day, week, month
    
    # Физиологические показатели
    sleep_quality = Column(Integer, nullable=True)  # Качество сна (0-100)
    sleep_duration_minutes = Column(Integer, nullable=True)  # Продолжительность сна в минутах
    physical_activity_minutes = Column(Integer, nullable=True)  # Физическая активность в минутах
    nutrition_quality = Column(Integer, nullable=True)  # Качество питания (0-100)
    
    # Агрегированные значения по категориям потребностей
    physical_needs_satisfaction = Column(Integer, nullable=True)  # Физические потребности (0-100)
    emotional_needs_satisfaction = Column(Integer, nullable=True)  # Эмоциональные потребности (0-100)
    cognitive_needs_satisfaction = Column(Integer, nullable=True)  # Когнитивные потребности (0-100)
    social_needs_satisfaction = Column(Integer, nullable=True)  # Социальные потребности (0-100)
    spiritual_needs_satisfaction = Column(Integer, nullable=True)  # Духовные потребности (0-100)
    need_satisfaction = Column(JSONB, nullable=True)  # Детальная оценка удовлетворенности потребностей
    
    # Общий показатель благополучия
    wellbeing_index = Column(Float, nullable=True)  # Индекс благополучия (0-100)
    
    # Погодные условия
    weather_conditions = Column(JSONB, nullable=True)  # Погодные условия
    
    # Связанные активности
    related_activities = Column(ARRAY(UUID(as_uuid=True)), nullable=True)  # Связанные активности
    
    # Источник данных
    source = Column(String(50), nullable=False)  # manual, automated, wearable, calculated
    source_details = Column(JSONB, nullable=True)  # Детали источника данных
    
    # Дополнительные параметры
    notes = Column(Text, nullable=True)  # Заметки/комментарии
    tags = Column(JSONB, nullable=True)  # Теги/метки
    weather_data = Column(JSONB, nullable=True)  # Данные о погоде
    location_data = Column(JSONB, nullable=True)  # Данные о местоположении
    state_metadata = Column(JSONB, nullable=True)  # Метаданные
    
    # Внешняя активность, связанная с состоянием
    activity_id = Column(UUID(as_uuid=True), ForeignKey("activities.id", ondelete="SET NULL"), nullable=True)
    activity_schedule_id = Column(UUID(as_uuid=True), ForeignKey("activity_schedules.id", ondelete="SET NULL"), nullable=True)
    
    # Валидационные ограничения
    __table_args__ = (
        CheckConstraint("mood_score BETWEEN -10.0 AND 10.0 OR mood_score IS NULL", name="check_mood_range"),
        CheckConstraint("energy_level BETWEEN -10.0 AND 10.0 OR energy_level IS NULL", name="check_energy_range"),
        CheckConstraint("stress_level BETWEEN 0.0 AND 10.0 OR stress_level IS NULL", name="check_stress_range"),
        CheckConstraint("anxiety_level BETWEEN 0.0 AND 10.0 OR anxiety_level IS NULL", name="check_anxiety_range"),
        CheckConstraint("focus_level BETWEEN 0 AND 100 OR focus_level IS NULL", name="check_focus_range"),
        CheckConstraint("motivation_level BETWEEN 0 AND 100 OR motivation_level IS NULL", name="check_motivation_range"),
        CheckConstraint("sleep_quality BETWEEN 0 AND 100 OR sleep_quality IS NULL", name="check_sleep_quality_range"),
        CheckConstraint("wellbeing_index BETWEEN 0 AND 100 OR wellbeing_index IS NULL", name="check_wellbeing_range"),
        CheckConstraint("source IN ('manual', 'automated', 'wearable', 'calculated')", name="check_source_type"),
        CheckConstraint("period_type IN ('instant', 'day', 'week', 'month')", name="check_period_type"),
    )
    
    # Отношения
    user = relationship("User", backref="states")
    activity = relationship("Activity", backref="states")
    schedule = relationship("ActivitySchedule", backref="states")
    
    def __repr__(self):
        return f"<UserState(user_id='{self.user_id}', timestamp='{self.timestamp}', wellbeing={self.wellbeing_index})>"
    
    def calculate_wellbeing_index(self):
        """
        Рассчитывает общий индекс благополучия на основе различных показателей состояния.
        Формула может быть настроена в соответствии с требованиями приложения.
        """
        # Список показателей с весами и диапазонами
        indicators = [
            # (значение, вес, обратный?, исходный_мин, исходный_макс)
            (self.energy_level, 1.0, False, -10.0, 10.0),
            (self.mood_score, 1.2, False, -10.0, 10.0),
            (self.stress_level, 0.8, True, 0.0, 10.0),  # Обратный показатель (ниже = лучше)
            (self.anxiety_level, 0.8, True, 0.0, 10.0),  # Обратный показатель
            (self.focus_level, 0.9, False, 0, 100),
            (self.motivation_level, 1.0, False, 0, 100),
            (self.sleep_quality, 1.1, False, 0, 100),
            (self.physical_needs_satisfaction, 1.0, False, 0, 100),
            (self.emotional_needs_satisfaction, 1.0, False, 0, 100),
            (self.cognitive_needs_satisfaction, 0.9, False, 0, 100),
            (self.social_needs_satisfaction, 0.9, False, 0, 100),
            (self.spiritual_needs_satisfaction, 0.8, False, 0, 100)
        ]
        
        valid_indicators = []
        total_weight = 0
        
        for indicator_data in indicators:
            value, weight, is_inverse, min_val, max_val = indicator_data
            
            if value is not None:
                # Нормализуем значение к шкале 0-100
                normalized_value = (value - min_val) / (max_val - min_val) * 100
                
                # Для обратных показателей (ниже = лучше), преобразуем в прямой (выше = лучше)
                adjusted_value = 100 - normalized_value if is_inverse else normalized_value
                valid_indicators.append((adjusted_value, weight))
                total_weight += weight
        
        if not valid_indicators:
            return None
        
        # Рассчитываем взвешенное среднее значение индикаторов
        weighted_sum = sum(value * weight for value, weight in valid_indicators)
        self.wellbeing_index = weighted_sum / total_weight if total_weight > 0 else None
        
        return self.wellbeing_index
    
    @classmethod
    def get_daily_average(cls, user_id, date):
        """
        Возвращает среднее значение состояния пользователя за указанный день.
        Метод для использования в запросах SQLAlchemy.
        """
        from sqlalchemy import func, cast, Date
        from app.core.database import get_db_context
        
        start_date = datetime.combine(date, datetime.min.time())
        end_date = datetime.combine(date, datetime.max.time())
        
        # Пример SQL-запроса (для документации метода)
        """
        SELECT 
            AVG(energy_level) as avg_energy,
            AVG(mood_level) as avg_mood,
            AVG(stress_level) as avg_stress,
            AVG(wellbeing_index) as avg_wellbeing
        FROM user_states
        WHERE 
            user_id = :user_id AND
            timestamp BETWEEN :start_date AND :end_date
        """
        
        # Реальная реализация будет использоваться в сервисах
        pass
    
    @classmethod
    def get_weekly_trend(cls, user_id, end_date=None):
        """
        Возвращает тренд состояния пользователя за последнюю неделю.
        Метод для использования в запросах SQLAlchemy.
        """
        from sqlalchemy import func, cast, Date
        from app.core.database import get_db_context
        
        if end_date is None:
            end_date = datetime.now().date()
        
        start_date = end_date - timedelta(days=7)
        
        # Пример SQL-запроса (для документации метода)
        """
        SELECT 
            CAST(timestamp AS DATE) as date,
            AVG(wellbeing_index) as avg_wellbeing
        FROM user_states
        WHERE 
            user_id = :user_id AND
            timestamp BETWEEN :start_date AND :end_date
        GROUP BY CAST(timestamp AS DATE)
        ORDER BY date
        """
        
        # Реальная реализация будет использоваться в сервисах
        pass