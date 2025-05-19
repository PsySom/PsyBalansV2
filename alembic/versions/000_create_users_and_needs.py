"""Create users and needs tables

Revision ID: 000_create_users_and_needs
Revises: 
Create Date: 2025-05-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '000_create_users_and_needs'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Создает базовые таблицы:
    - users - таблица пользователей
    - need_categories - категории потребностей
    - needs - потребности
    """
    # 1. Создаем таблицу пользователей
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('username', sa.String(50), nullable=True, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(50), nullable=True),
        sa.Column('last_name', sa.String(50), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('date_of_birth', sa.Date, nullable=True),
        sa.Column('gender', sa.String(20), nullable=True),
        sa.Column('timezone', sa.String(50), nullable=True, server_default=sa.text("'UTC'")),
        sa.Column('language', sa.String(10), nullable=True, server_default=sa.text("'ru'")),
        sa.Column('profile_picture', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('is_verified', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('is_staff', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('is_superuser', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('last_login', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_users_email', 'email'),
        sa.Index('ix_users_username', 'username')
    )
    
    # 2. Создаем таблицу категорий потребностей
    op.create_table(
        'need_categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('icon', sa.String(100), nullable=True),
        sa.Column('color', sa.String(20), nullable=True),
        sa.Column('priority', sa.Integer, nullable=False, server_default=sa.text('100')),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_need_categories_slug', 'slug'),
        sa.Index('ix_need_categories_priority', 'priority')
    )
    
    # 3. Создаем таблицу потребностей
    op.create_table(
        'needs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('icon', sa.String(100), nullable=True),
        sa.Column('color', sa.String(20), nullable=True),
        sa.Column('priority', sa.Integer, nullable=False, server_default=sa.text('100')),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['category_id'], ['need_categories.id'], name='fk_need_category'),
        sa.UniqueConstraint('category_id', 'slug', name='uq_need_category_slug'),
        sa.Index('ix_needs_category_id', 'category_id'),
        sa.Index('ix_needs_priority', 'priority')
    )


def downgrade() -> None:
    """
    Удаляет созданные таблицы в обратном порядке.
    """
    op.drop_table('needs')
    op.drop_table('need_categories')
    op.drop_table('users')