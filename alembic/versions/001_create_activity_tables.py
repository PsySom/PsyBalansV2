"""Create activity tables

Revision ID: 001_create_activity_tables
Revises: 000_create_users_and_needs
Create Date: 2025-05-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_create_activity_tables'
down_revision: Union[str, None] = '000_create_users_and_needs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Создает таблицы для активностей:
    - activity_types - типы активностей
    - activity_subtypes - подтипы активностей 
    - activities - основная таблица активностей
    """
    # 1. Создаем таблицу типов активностей
    op.create_table(
        'activity_types',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('icon', sa.String(100), nullable=True),
        sa.Column('color', sa.String(20), nullable=True),
        sa.Column('priority', sa.Integer, nullable=False, server_default=sa.text('100')),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('is_default', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_activity_types_slug', 'slug'),
        sa.Index('ix_activity_types_priority', 'priority')
    )
    
    # 2. Создаем таблицу подтипов активностей
    op.create_table(
        'activity_subtypes',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('activity_type_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('icon', sa.String(100), nullable=True),
        sa.Column('color', sa.String(20), nullable=True),
        sa.Column('priority', sa.Integer, nullable=False, server_default=sa.text('100')),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('is_default', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['activity_type_id'], ['activity_types.id'], name='fk_activity_subtype_type'),
        sa.UniqueConstraint('activity_type_id', 'slug', name='uq_activity_subtype_type_slug'),
        sa.Index('ix_activity_subtypes_type_id', 'activity_type_id'),
        sa.Index('ix_activity_subtypes_priority', 'priority')
    )
    
    # 3. Создаем основную таблицу активностей
    op.create_table(
        'activities',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('activity_type_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('activity_subtype_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('duration_minutes', sa.Integer, nullable=True),
        sa.Column('energy_required', sa.Integer, nullable=True, comment='Шкала 1-10: сколько энергии требует активность'),
        sa.Column('difficulty', sa.Integer, nullable=True, comment='Шкала 1-10: насколько сложна активность'),
        sa.Column('enjoyment', sa.Integer, nullable=True, comment='Шкала 1-10: насколько приятна активность'),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('is_favorite', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('is_public', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('is_template', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('use_count', sa.Integer, nullable=False, server_default=sa.text('0')),
        sa.Column('last_used_at', sa.DateTime, nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_activity_user'),
        sa.ForeignKeyConstraint(['activity_type_id'], ['activity_types.id'], name='fk_activity_type'),
        sa.ForeignKeyConstraint(['activity_subtype_id'], ['activity_subtypes.id'], name='fk_activity_subtype'),
        sa.Index('ix_activities_user_id', 'user_id'),
        sa.Index('ix_activities_type_id', 'activity_type_id'),
        sa.Index('ix_activities_subtype_id', 'activity_subtype_id'),
        sa.Index('ix_activities_is_favorite', 'is_favorite'),
        sa.Index('ix_activities_is_public', 'is_public'),
        sa.Index('ix_activities_is_template', 'is_template'),
        sa.Index('ix_activities_last_used', 'last_used_at')
    )
    
    # 4. Создаем таблицу для связи активностей с потребностями
    op.create_table(
        'activity_needs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('activity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('need_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('satisfaction_level', sa.Integer, nullable=False, comment='Шкала 1-10: насколько активность удовлетворяет потребность'),
        sa.Column('is_primary', sa.Boolean, nullable=False, server_default=sa.text('false'), comment='Является ли потребность основной для активности'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['activity_id'], ['activities.id'], name='fk_activity_need_activity'),
        sa.ForeignKeyConstraint(['need_id'], ['needs.id'], name='fk_activity_need_need'),
        sa.UniqueConstraint('activity_id', 'need_id', name='uq_activity_need'),
        sa.Index('ix_activity_needs_activity_id', 'activity_id'),
        sa.Index('ix_activity_needs_need_id', 'need_id')
    )
    
    # 5. Создаем таблицу для оценок активностей пользователем
    op.create_table(
        'activity_evaluations',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('activity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('date', sa.Date, nullable=False, server_default=sa.text('current_date')),
        sa.Column('time_spent_minutes', sa.Integer, nullable=True),
        sa.Column('satisfaction_level', sa.Integer, nullable=False, comment='Шкала 1-10: уровень удовлетворенности от активности'),
        sa.Column('energy_before', sa.Integer, nullable=True, comment='Шкала 1-10: уровень энергии до активности'),
        sa.Column('energy_after', sa.Integer, nullable=True, comment='Шкала 1-10: уровень энергии после активности'),
        sa.Column('mood_before', sa.Integer, nullable=True, comment='Шкала 1-10: настроение до активности'),
        sa.Column('mood_after', sa.Integer, nullable=True, comment='Шкала 1-10: настроение после активности'),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('completion_percentage', sa.Integer, nullable=True, comment='Процент выполнения активности, если не была завершена'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_activity_evaluation_user'),
        sa.ForeignKeyConstraint(['activity_id'], ['activities.id'], name='fk_activity_evaluation_activity'),
        sa.Index('ix_activity_evaluations_user_id', 'user_id'),
        sa.Index('ix_activity_evaluations_activity_id', 'activity_id'),
        sa.Index('ix_activity_evaluations_date', 'date')
    )


def downgrade() -> None:
    """
    Удаляет созданные таблицы активностей в обратном порядке.
    """
    # Удаляем таблицы в обратном порядке, чтобы избежать ошибок с внешними ключами
    op.drop_table('activity_evaluations')
    op.drop_table('activity_needs')
    op.drop_table('activities')
    op.drop_table('activity_subtypes')
    op.drop_table('activity_types')