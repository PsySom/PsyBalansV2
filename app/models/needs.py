from sqlalchemy import Column, String, Text, ForeignKey, UniqueConstraint, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import uuid


class NeedCategory(BaseModel):
    """Модель категории потребностей
    
    Примеры: физические, эмоциональные, интеллектуальные, социальные, духовные
    """
    __tablename__ = "need_categories"
    
    name = Column(String(50), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    color = Column(String(7), nullable=True)  # HEX-код цвета
    icon = Column(String(50), nullable=True)  # Имя иконки или путь к ней
    display_order = Column(Integer, default=0, nullable=False)  # Порядок отображения
    
    # Отношения
    needs = relationship("Need", back_populates="category", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<NeedCategory(name='{self.name}')>"


class Need(BaseModel):
    """Модель потребности пользователя
    
    Представляет собой конкретную потребность пользователя, которую он стремится удовлетворить
    через свои активности. Каждая потребность относится к определенной категории.
    
    Примеры:
    - Физические: сон, питание, физическая активность
    - Эмоциональные: радость, удовольствие, безопасность
    - Интеллектуальные: обучение, творчество, решение проблем
    - Социальные: общение, признание, принадлежность
    - Духовные: смысл, ценности, трансцендентность
    """
    __tablename__ = "needs"
    
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("need_categories.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_custom = Column(Boolean, default=False, nullable=False)  # Флаг, указывающий, является ли потребность пользовательской
    importance = Column(Integer, default=3, nullable=False)  # Важность потребности по шкале от 1 до 5
    
    # Уникальное ограничение: имя потребности должно быть уникальным для пользователя
    __table_args__ = (UniqueConstraint("name", "user_id", name="uix_name_user"),)
    
    # Отношения
    category = relationship("NeedCategory", back_populates="needs")
    user = relationship("User", back_populates="needs")
    activity_needs = relationship("ActivityNeed", back_populates="need", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Need(name='{self.name}', category='{self.category.name if self.category else None}')>"