from sqlalchemy import Column, String, Boolean, ForeignKey, Text, Integer, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from app.models.role import user_role


class UserProfile(BaseModel):
    """
    Модель профиля пользователя с дополнительной информацией.
    """
    __tablename__ = "user_profiles"
    
    user_id = Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    bio = Column(Text, nullable=True)
    avatar_url = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    country = Column(String, nullable=True)
    city = Column(String, nullable=True)
    timezone = Column(String, nullable=True)
    language = Column(String, nullable=True, default="ru")
    preferences = Column(JSONB, nullable=True, default={})
    
    # Отношения
    user = relationship("User", back_populates="profile")


class UserSecurityInfo(BaseModel):
    """
    Модель для хранения информации о безопасности пользователя.
    """
    __tablename__ = "user_security_info"
    
    user_id = Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    last_login_at = Column(String, nullable=True)
    last_login_ip = Column(String, nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    last_password_change = Column(DateTime, nullable=True)
    password_reset_token = Column(String, nullable=True)
    password_reset_expires = Column(DateTime, nullable=True)
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String, nullable=True)
    
    # Отношения
    user = relationship("User", back_populates="security_info")


class User(BaseModel):
    """Модель пользователя системы"""
    __tablename__ = "users"

    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    is_superuser = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)
    
    # Отношения
    activities = relationship("Activity", back_populates="user", cascade="all, delete-orphan")
    needs = relationship("Need", back_populates="user", cascade="all, delete-orphan")
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    security_info = relationship("UserSecurityInfo", back_populates="user", uselist=False, cascade="all, delete-orphan")
    roles = relationship("Role", secondary=user_role, back_populates="users")
    
    @property
    def full_name(self) -> str:
        """Возвращает полное имя пользователя"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        return ""
    
    def has_permission(self, resource: str, action: str) -> bool:
        """
        Проверяет, имеет ли пользователь указанное разрешение.
        
        Args:
            resource: Ресурс (например, "users", "activities")
            action: Действие (например, "read", "write", "delete")
            
        Returns:
            True, если пользователь имеет указанное разрешение, иначе False
        """
        # Суперпользователь имеет все разрешения
        if self.is_superuser:
            return True
        
        # Проверяем разрешения через роли пользователя
        for role in self.roles:
            for permission in role.permissions:
                if permission.resource == resource and permission.action == action:
                    return True
        
        return False