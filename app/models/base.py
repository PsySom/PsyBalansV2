from sqlalchemy import Column, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.core.database.postgresql import Base


class BaseModel(Base):
    """Базовая модель для всех моделей приложения
    
    Предоставляет общие поля, которые должны быть во всех моделях:
    - id: UUID первичный ключ 
    - created_at: время создания записи
    - updated_at: время последнего обновления записи
    - is_active: флаг активности записи
    """
    __abstract__ = True
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True, nullable=False)