"""
Модель для ролей и прав доступа пользователей.
"""
from sqlalchemy import Column, String, Table, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


# Связующая таблица между пользователями и ролями (many-to-many)
user_role = Table(
    "user_roles",
    BaseModel.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
)

# Связующая таблица между ролями и правами (many-to-many)
role_permission = Table(
    "role_permissions",
    BaseModel.metadata,
    Column("role_id", UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)
)


class Role(BaseModel):
    """
    Модель роли пользователя.
    
    Роли определяют наборы прав доступа для пользователей.
    Примеры: admin, user, therapist, etc.
    """
    __tablename__ = "roles"
    
    name = Column(String, nullable=False, unique=True, index=True)
    description = Column(String, nullable=True)
    
    # Отношения
    users = relationship("User", secondary=user_role, back_populates="roles")
    permissions = relationship("Permission", secondary=role_permission, back_populates="roles")
    
    def __str__(self):
        return self.name


class Permission(BaseModel):
    """
    Модель права доступа.
    
    Права доступа определяют конкретные действия, которые может выполнять пользователь.
    Примеры: users:read, users:write, activities:create, etc.
    """
    __tablename__ = "permissions"
    
    name = Column(String, nullable=False, unique=True, index=True)
    description = Column(String, nullable=True)
    resource = Column(String, nullable=False, index=True)  # users, activities, needs, etc.
    action = Column(String, nullable=False)  # read, write, delete, etc.
    
    # Отношения
    roles = relationship("Role", secondary=role_permission, back_populates="permissions")
    
    # Ограничение уникальности для пары resource-action
    __table_args__ = (
        UniqueConstraint('resource', 'action', name='uq_permission_resource_action'),
    )
    
    def __str__(self):
        return f"{self.resource}:{self.action}"