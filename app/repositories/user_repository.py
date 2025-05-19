"""
Репозиторий для работы с пользователями системы.
"""
from typing import Optional, List, Dict, Any, Union, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, or_, and_, func, text
from sqlalchemy.sql import Select
from sqlalchemy.orm import joinedload
from uuid import UUID

from app.models.user import User, UserProfile, UserSecurityInfo
from app.models.role import Role, Permission
from app.repositories.base_repository import BaseRepository
from app.core.security import get_password_hash, verify_password


class UserRepository(BaseRepository[User]):
    """
    Репозиторий для работы с пользователями системы.
    Предоставляет методы для управления пользователями, их профилями,
    безопасностью и правами доступа.
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Инициализация репозитория с сессией базы данных.
        
        Args:
            db_session: Асинхронная сессия SQLAlchemy
        """
        super().__init__(db_session, User)
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Получение пользователя по email.
        
        Args:
            email: Email пользователя
            
        Returns:
            Пользователь или None, если не найден
        """
        query = select(self.model).where(self.model.email == email, self.model.is_active == True)
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_full_profile(self, user_id: UUID) -> Optional[User]:
        """
        Получение полного профиля пользователя со всеми связанными данными.
        
        Args:
            user_id: Идентификатор пользователя
            
        Returns:
            Пользователь со всеми загруженными отношениями или None
        """
        query = (
            select(self.model)
            .where(self.model.id == user_id)
            .options(
                joinedload(self.model.profile),
                joinedload(self.model.security_info),
                joinedload(self.model.roles).joinedload(Role.permissions)
            )
        )
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def create_with_profile(self, user_data: Dict[str, Any]) -> User:
        """
        Создание пользователя вместе с профилем.
        
        Args:
            user_data: Словарь с данными пользователя и профиля
            
        Returns:
            Созданный пользователь
        """
        # Извлекаем данные профиля из общего словаря
        profile_data = user_data.pop("profile", {})
        security_data = user_data.pop("security_info", {})
        
        # Если есть пароль, хешируем его
        if "password" in user_data:
            user_data["hashed_password"] = get_password_hash(user_data.pop("password"))
        
        # Создаем пользователя
        user = await self.create(user_data)
        
        # Если есть данные профиля, создаем профиль
        if profile_data:
            profile_data["user_id"] = user.id
            profile = UserProfile(**profile_data)
            self.db.add(profile)
        
        # Если есть данные безопасности, создаем запись о безопасности
        if security_data:
            security_data["user_id"] = user.id
            security_info = UserSecurityInfo(**security_data)
            self.db.add(security_info)
        
        await self.db.flush()
        
        return user
    
    async def update_profile(self, user_id: UUID, profile_data: Dict[str, Any]) -> Optional[UserProfile]:
        """
        Обновление профиля пользователя.
        
        Args:
            user_id: Идентификатор пользователя
            profile_data: Словарь с обновленными данными профиля
            
        Returns:
            Обновленный профиль или None, если пользователь не найден
        """
        # Проверяем существование пользователя
        user = await self.get_by_id(user_id)
        if not user:
            return None
        
        # Проверяем наличие профиля
        query = select(UserProfile).where(UserProfile.user_id == user_id)
        result = await self.db.execute(query)
        profile = result.scalars().first()
        
        if profile:
            # Обновляем существующий профиль
            for key, value in profile_data.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
        else:
            # Создаем новый профиль
            profile_data["user_id"] = user_id
            profile = UserProfile(**profile_data)
            self.db.add(profile)
        
        await self.db.flush()
        await self.db.refresh(profile)
        return profile
    
    async def update_security_info(self, user_id: UUID, security_data: Dict[str, Any]) -> Optional[UserSecurityInfo]:
        """
        Обновление информации о безопасности пользователя.
        
        Args:
            user_id: Идентификатор пользователя
            security_data: Словарь с обновленными данными безопасности
            
        Returns:
            Обновленная информация о безопасности или None, если пользователь не найден
        """
        # Проверяем существование пользователя
        user = await self.get_by_id(user_id)
        if not user:
            return None
        
        # Проверяем наличие информации о безопасности
        query = select(UserSecurityInfo).where(UserSecurityInfo.user_id == user_id)
        result = await self.db.execute(query)
        security_info = result.scalars().first()
        
        if security_info:
            # Обновляем существующую информацию
            for key, value in security_data.items():
                if hasattr(security_info, key):
                    setattr(security_info, key, value)
        else:
            # Создаем новую запись
            security_data["user_id"] = user_id
            security_info = UserSecurityInfo(**security_data)
            self.db.add(security_info)
        
        await self.db.flush()
        await self.db.refresh(security_info)
        return security_info
    
    async def change_password(self, user_id: UUID, old_password: str, new_password: str) -> bool:
        """
        Изменение пароля пользователя с проверкой старого пароля.
        
        Args:
            user_id: Идентификатор пользователя
            old_password: Старый пароль
            new_password: Новый пароль
            
        Returns:
            True если пароль успешно изменен, иначе False
        """
        user = await self.get_by_id(user_id)
        if not user:
            return False
        
        # Проверяем старый пароль
        if not verify_password(old_password, user.hashed_password):
            return False
        
        # Обновляем пароль
        hashed_password = get_password_hash(new_password)
        user.hashed_password = hashed_password
        
        # Обновляем информацию о последнем изменении пароля
        security_info = user.security_info
        if security_info:
            from datetime import datetime
            security_info.last_password_change = datetime.utcnow()
            security_info.password_reset_token = None
            security_info.password_reset_expires = None
        
        await self.db.flush()
        return True
    
    async def reset_password(self, user_id: UUID, new_password: str) -> bool:
        """
        Сброс пароля пользователя без проверки старого (для администраторов или процедуры восстановления).
        
        Args:
            user_id: Идентификатор пользователя
            new_password: Новый пароль
            
        Returns:
            True если пароль успешно сброшен, иначе False
        """
        user = await self.get_by_id(user_id)
        if not user:
            return False
        
        # Обновляем пароль
        hashed_password = get_password_hash(new_password)
        user.hashed_password = hashed_password
        
        # Обновляем информацию о последнем изменении пароля
        security_info = user.security_info
        if security_info:
            from datetime import datetime
            security_info.last_password_change = datetime.utcnow()
            security_info.password_reset_token = None
            security_info.password_reset_expires = None
            security_info.failed_login_attempts = 0
        
        await self.db.flush()
        return True
    
    async def search_users(
        self, 
        search_term: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        pagination: Optional[Dict[str, int]] = None,
        order_by: Optional[List[str]] = None
    ) -> Tuple[List[User], int]:
        """
        Поиск пользователей по различным критериям.
        
        Args:
            search_term: Строка поиска (ищет в email, имени и фамилии)
            filters: Дополнительные фильтры
            pagination: Параметры пагинации
            order_by: Параметры сортировки
            
        Returns:
            Кортеж из списка пользователей и общего количества найденных записей
        """
        query = select(self.model)
        count_query = select(func.count()).select_from(self.model)
        
        # Применяем поисковый запрос
        if search_term:
            search_filter = or_(
                self.model.email.ilike(f"%{search_term}%"),
                self.model.first_name.ilike(f"%{search_term}%"),
                self.model.last_name.ilike(f"%{search_term}%")
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)
        
        # Применяем дополнительные фильтры
        if filters:
            for field_name, value in filters.items():
                if hasattr(self.model, field_name):
                    if isinstance(value, dict) and 'op' in value:
                        op = value['op']
                        val = value['value']
                        field = getattr(self.model, field_name)
                        
                        if op == 'eq':
                            query = query.where(field == val)
                            count_query = count_query.where(field == val)
                        elif op == 'ne':
                            query = query.where(field != val)
                            count_query = count_query.where(field != val)
                        elif op == 'gt':
                            query = query.where(field > val)
                            count_query = count_query.where(field > val)
                        elif op == 'lt':
                            query = query.where(field < val)
                            count_query = count_query.where(field < val)
                        elif op == 'ge':
                            query = query.where(field >= val)
                            count_query = count_query.where(field >= val)
                        elif op == 'le':
                            query = query.where(field <= val)
                            count_query = count_query.where(field <= val)
                        elif op == 'like':
                            query = query.where(field.like(f"%{val}%"))
                            count_query = count_query.where(field.like(f"%{val}%"))
                        elif op == 'in':
                            query = query.where(field.in_(val))
                            count_query = count_query.where(field.in_(val))
                    else:
                        query = query.where(getattr(self.model, field_name) == value)
                        count_query = count_query.where(getattr(self.model, field_name) == value)
        
        # Получаем общее количество записей
        result = await self.db.execute(count_query)
        total_count = result.scalar()
        
        # Применяем сортировку
        if order_by:
            for field_name in order_by:
                if field_name.startswith('-'):
                    field_name = field_name[1:]
                    if hasattr(self.model, field_name):
                        query = query.order_by(getattr(self.model, field_name).desc())
                else:
                    if hasattr(self.model, field_name):
                        query = query.order_by(getattr(self.model, field_name).asc())
        
        # Применяем пагинацию
        if pagination:
            skip = pagination.get('skip', 0)
            limit = pagination.get('limit', 100)
            query = query.offset(skip).limit(limit)
        
        # Получаем результаты
        result = await self.db.execute(query)
        return result.scalars().all(), total_count
    
    async def assign_role(self, user_id: UUID, role_id: UUID) -> bool:
        """
        Назначение роли пользователю.
        
        Args:
            user_id: Идентификатор пользователя
            role_id: Идентификатор роли
            
        Returns:
            True если роль успешно назначена, иначе False
        """
        # Проверяем существование пользователя
        user = await self.get_by_id(user_id)
        if not user:
            return False
        
        # Проверяем существование роли
        role_query = select(Role).where(Role.id == role_id)
        result = await self.db.execute(role_query)
        role = result.scalars().first()
        if not role:
            return False
        
        # Проверяем, есть ли уже эта роль у пользователя
        # Для этого загружаем роли пользователя
        user_query = (
            select(self.model)
            .where(self.model.id == user_id)
            .options(joinedload(self.model.roles))
        )
        result = await self.db.execute(user_query)
        user_with_roles = result.scalars().first()
        
        # Проверяем наличие роли
        for existing_role in user_with_roles.roles:
            if existing_role.id == role_id:
                # Роль уже назначена
                return True
        
        # Добавляем роль
        user_with_roles.roles.append(role)
        await self.db.flush()
        return True
    
    async def remove_role(self, user_id: UUID, role_id: UUID) -> bool:
        """
        Удаление роли у пользователя.
        
        Args:
            user_id: Идентификатор пользователя
            role_id: Идентификатор роли
            
        Returns:
            True если роль успешно удалена, иначе False
        """
        # Загружаем пользователя с ролями
        user_query = (
            select(self.model)
            .where(self.model.id == user_id)
            .options(joinedload(self.model.roles))
        )
        result = await self.db.execute(user_query)
        user = result.scalars().first()
        
        if not user:
            return False
        
        # Ищем роль для удаления
        role_to_remove = None
        for role in user.roles:
            if role.id == role_id:
                role_to_remove = role
                break
        
        if not role_to_remove:
            # Роль не найдена
            return False
        
        # Удаляем роль
        user.roles.remove(role_to_remove)
        await self.db.flush()
        return True
    
    async def get_users_by_role(self, role_name: str) -> List[User]:
        """
        Получение списка пользователей с указанной ролью.
        
        Args:
            role_name: Название роли
            
        Returns:
            Список пользователей с указанной ролью
        """
        query = (
            select(self.model)
            .join(self.model.roles)
            .where(Role.name == role_name)
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def has_permission(self, user_id: UUID, resource: str, action: str) -> bool:
        """
        Проверка наличия у пользователя указанного разрешения.
        
        Args:
            user_id: Идентификатор пользователя
            resource: Ресурс (например, "users", "activities")
            action: Действие (например, "read", "write", "delete")
            
        Returns:
            True если пользователь имеет указанное разрешение, иначе False
        """
        # Загружаем пользователя с ролями и разрешениями
        user_query = (
            select(self.model)
            .where(self.model.id == user_id)
            .options(
                joinedload(self.model.roles).joinedload(Role.permissions)
            )
        )
        result = await self.db.execute(user_query)
        user = result.scalars().first()
        
        if not user:
            return False
        
        # Проверяем, является ли пользователь суперпользователем
        if user.is_superuser:
            return True
        
        # Проверяем разрешения через метод has_permission модели User
        return user.has_permission(resource, action)
    
    async def record_login_attempt(self, user_id: UUID, success: bool, ip_address: Optional[str] = None) -> None:
        """
        Запись информации о попытке входа в систему.
        
        Args:
            user_id: Идентификатор пользователя
            success: Успешность попытки
            ip_address: IP-адрес пользователя
        """
        # Проверяем наличие информации о безопасности
        query = select(UserSecurityInfo).where(UserSecurityInfo.user_id == user_id)
        result = await self.db.execute(query)
        security_info = result.scalars().first()
        
        if not security_info:
            # Создаем новую запись
            security_info = UserSecurityInfo(user_id=user_id)
            self.db.add(security_info)
        
        # Обновляем информацию
        from datetime import datetime
        
        if success:
            # Успешный вход
            security_info.last_login_at = datetime.utcnow().isoformat()
            security_info.last_login_ip = ip_address
            security_info.failed_login_attempts = 0
        else:
            # Неудачная попытка
            security_info.failed_login_attempts += 1
        
        await self.db.flush()
    
    async def get_inactive_users(self, days: int = 30) -> List[User]:
        """
        Получение списка неактивных пользователей.
        
        Args:
            days: Количество дней неактивности
            
        Returns:
            Список неактивных пользователей
        """
        from datetime import datetime, timedelta
        inactive_date = datetime.utcnow() - timedelta(days=days)
        
        # SQL запрос с использованием RAW SQL для сложной логики
        # Ищем пользователей, которые не логинились с указанной даты
        # или никогда не логинились (last_login_at IS NULL)
        query = text(f"""
            SELECT u.* FROM users u
            LEFT JOIN user_security_info usi ON u.id = usi.user_id
            WHERE u.is_active = true AND (
                usi.last_login_at < :inactive_date OR
                usi.last_login_at IS NULL
            )
        """)
        
        result = await self.db.execute(query, {"inactive_date": inactive_date.isoformat()})
        return result.scalars().all()
    
    async def bulk_activate(self, user_ids: List[UUID]) -> int:
        """
        Массовая активация пользователей.
        
        Args:
            user_ids: Список идентификаторов пользователей
            
        Returns:
            Количество активированных пользователей
        """
        query = (
            update(self.model)
            .where(self.model.id.in_(user_ids))
            .values(is_active=True)
        )
        result = await self.db.execute(query)
        await self.db.flush()
        return result.rowcount
    
    async def bulk_deactivate(self, user_ids: List[UUID]) -> int:
        """
        Массовая деактивация пользователей.
        
        Args:
            user_ids: Список идентификаторов пользователей
            
        Returns:
            Количество деактивированных пользователей
        """
        query = (
            update(self.model)
            .where(self.model.id.in_(user_ids))
            .values(is_active=False)
        )
        result = await self.db.execute(query)
        await self.db.flush()
        return result.rowcount
    
    async def verify_email(self, token: str) -> Optional[User]:
        """
        Верификация email пользователя по токену.
        
        Args:
            token: Токен верификации
            
        Returns:
            Пользователь, чей email был подтвержден, или None
        """
        # Ищем пользователя с указанным токеном
        query = select(self.model).where(self.model.verification_token == token)
        result = await self.db.execute(query)
        user = result.scalars().first()
        
        if not user:
            return None
        
        # Подтверждаем email
        user.email_verified = True
        user.verification_token = None
        await self.db.flush()
        return user
    
    async def generate_email_verification_token(self, user_id: UUID) -> Optional[str]:
        """
        Генерация токена для верификации email.
        
        Args:
            user_id: Идентификатор пользователя
            
        Returns:
            Сгенерированный токен или None
        """
        import secrets
        
        user = await self.get_by_id(user_id)
        if not user:
            return None
        
        # Генерируем токен
        token = secrets.token_urlsafe(32)
        user.verification_token = token
        await self.db.flush()
        return token
    
    async def generate_password_reset_token(self, email: str) -> Optional[Tuple[UUID, str]]:
        """
        Генерация токена для сброса пароля.
        
        Args:
            email: Email пользователя
            
        Returns:
            Кортеж из ID пользователя и токена или None
        """
        import secrets
        from datetime import datetime, timedelta
        
        # Ищем пользователя по email
        user = await self.get_by_email(email)
        if not user:
            return None
        
        # Получаем или создаем запись о безопасности
        query = select(UserSecurityInfo).where(UserSecurityInfo.user_id == user.id)
        result = await self.db.execute(query)
        security_info = result.scalars().first()
        
        if not security_info:
            security_info = UserSecurityInfo(user_id=user.id)
            self.db.add(security_info)
            await self.db.flush()
        
        # Генерируем токен
        token = secrets.token_urlsafe(32)
        security_info.password_reset_token = token
        security_info.password_reset_expires = datetime.utcnow() + timedelta(hours=24)
        
        await self.db.flush()
        return user.id, token
    
    async def verify_password_reset_token(self, token: str) -> Optional[UUID]:
        """
        Проверка токена для сброса пароля.
        
        Args:
            token: Токен сброса пароля
            
        Returns:
            ID пользователя, которому принадлежит токен, или None
        """
        from datetime import datetime
        
        # Ищем запись с указанным токеном
        query = select(UserSecurityInfo).where(
            UserSecurityInfo.password_reset_token == token,
            UserSecurityInfo.password_reset_expires > datetime.utcnow()
        )
        result = await self.db.execute(query)
        security_info = result.scalars().first()
        
        if not security_info:
            return None
        
        return security_info.user_id