from sqlalchemy import Column, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import uuid


class ActivityType(BaseModel):
    """Модель типа активности (основная классификация)
    
    Примеры: физические, социальные, интеллектуальные, творческие, духовные
    """
    __tablename__ = "activity_types"
    
    name = Column(String(50), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    color = Column(String(7), nullable=True)  # HEX-код цвета (например, #FF5733)
    icon = Column(String(50), nullable=True)  # Имя иконки или путь к ней
    
    # Отношения
    subtypes = relationship("ActivitySubtype", back_populates="activity_type", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="activity_type")
    
    def __repr__(self):
        return f"<ActivityType(name='{self.name}')>"


class ActivitySubtype(BaseModel):
    """Модель подтипа активности (детальная классификация)
    
    Примеры для физического типа: бег, йога, плавание, тренировка силы
    """
    __tablename__ = "activity_subtypes"
    
    name = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    activity_type_id = Column(UUID(as_uuid=True), ForeignKey("activity_types.id", ondelete="CASCADE"), nullable=False)
    color = Column(String(7), nullable=True)  # HEX-код цвета (например, #FF5733)
    icon = Column(String(50), nullable=True)  # Имя иконки или путь к ней
    
    # Уникальное ограничение: имя подтипа должно быть уникальным в рамках типа
    __table_args__ = (UniqueConstraint("name", "activity_type_id", name="uix_name_type"),)
    
    # Отношения
    activity_type = relationship("ActivityType", back_populates="subtypes")
    activities = relationship("Activity", back_populates="activity_subtype")
    
    def __repr__(self):
        return f"<ActivitySubtype(name='{self.name}', type='{self.activity_type.name if self.activity_type else None}')>"