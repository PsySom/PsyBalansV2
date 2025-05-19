"""Create needs and related tables

Revision ID: 003_create_needs_tables
Revises: 002_create_exercises_tables
Create Date: 2025-05-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003_create_needs_tables'
down_revision: Union[str, None] = '002_create_exercises_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Создает или обновляет таблицы для потребностей:
    - user_needs - потребности пользователя
    - user_need_history - история удовлетворенности потребностей
    - activity_need_links - связи между активностями и потребностями (если отсутствует)
    
    Примечание: таблицы need_categories и needs уже созданы в миграции 000_create_users_and_needs.
    """
    # Проверяем наличие таблицы activity_needs (создана в 001_create_activity_tables.py)
    # Если отсутствует, создаем activity_need_links
    # Эта проверка необходима, поскольку мы не хотим создавать дублирующие таблицы
    connection = op.get_bind()
    metadata = sa.MetaData()
    metadata.reflect(bind=connection, only=['activity_needs'])
    
    # Если таблица activity_needs не существует, создаем activity_need_links
    if 'activity_needs' not in metadata.tables:
        # 1. Создаем таблицу для связи активностей и потребностей
        op.create_table(
            'activity_need_links',
            sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
            sa.Column('activity_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('need_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('satisfaction_level', sa.Integer, nullable=False, comment='Оценка от 1 до 10: насколько активность удовлетворяет потребность'),
            sa.Column('is_primary', sa.Boolean, nullable=False, server_default=sa.text('false'), comment='Является ли потребность основной для активности'),
            sa.Column('notes', sa.Text, nullable=True),
            sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['activity_id'], ['activities.id'], name='fk_activity_need_link_activity'),
            sa.ForeignKeyConstraint(['need_id'], ['needs.id'], name='fk_activity_need_link_need'),
            sa.UniqueConstraint('activity_id', 'need_id', name='uq_activity_need_link'),
            sa.Index('ix_activity_need_links_activity_id', 'activity_id'),
            sa.Index('ix_activity_need_links_need_id', 'need_id')
        )
    
    # 2. Создаем таблицу потребностей пользователя
    op.create_table(
        'user_needs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('need_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('importance', sa.Integer, nullable=False, comment='Важность потребности для пользователя (1-10)'),
        sa.Column('current_satisfaction', sa.Integer, nullable=False, comment='Текущая степень удовлетворенности (1-10)'),
        sa.Column('target_satisfaction', sa.Integer, nullable=True, comment='Целевая степень удовлетворенности (1-10)'),
        sa.Column('satisfaction_frequency', sa.String(20), nullable=True, comment='Как часто пользователь хочет удовлетворять потребность'),
        sa.Column('status', sa.String(20), nullable=False, server_default=sa.text("'active'"), comment='active, paused, completed'),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('personal_strategies', sa.Text, nullable=True, comment='Личные стратегии пользователя для удовлетворения потребности'),
        sa.Column('is_favorite', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('is_hidden', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('last_updated', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_user_need_user'),
        sa.ForeignKeyConstraint(['need_id'], ['needs.id'], name='fk_user_need_need'),
        sa.UniqueConstraint('user_id', 'need_id', name='uq_user_need'),
        sa.Index('ix_user_needs_user_id', 'user_id'),
        sa.Index('ix_user_needs_need_id', 'need_id'),
        sa.Index('ix_user_needs_importance', 'importance'),
        sa.Index('ix_user_needs_satisfaction', 'current_satisfaction'),
        sa.Index('ix_user_needs_status', 'status')
    )
    
    # 3. Создаем таблицу истории удовлетворенности потребностей
    op.create_table(
        'user_need_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('need_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('date', sa.Date, nullable=False, server_default=sa.text('current_date')),
        sa.Column('satisfaction_level', sa.Integer, nullable=False, comment='Оценка удовлетворенности (1-10)'),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('related_activities', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True, comment='Связанные с этой оценкой активности'),
        sa.Column('feelings', postgresql.ARRAY(sa.String), nullable=True, comment='Чувства, связанные с этой потребностью'),
        sa.Column('context', sa.String(100), nullable=True, comment='Контекст, в котором была сделана оценка'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_user_need_history_user'),
        sa.ForeignKeyConstraint(['need_id'], ['needs.id'], name='fk_user_need_history_need'),
        sa.Index('ix_user_need_history_user_id', 'user_id'),
        sa.Index('ix_user_need_history_need_id', 'need_id'),
        sa.Index('ix_user_need_history_date', 'date'),
        sa.Index('ix_user_need_history_satisfaction', 'satisfaction_level')
    )
    
    # 4. Создаем таблицу для планов удовлетворения потребностей
    op.create_table(
        'need_fulfillment_plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_need_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('start_date', sa.Date, nullable=True),
        sa.Column('end_date', sa.Date, nullable=True),
        sa.Column('target_satisfaction', sa.Integer, nullable=True, comment='Целевой уровень удовлетворенности (1-10)'),
        sa.Column('status', sa.String(20), nullable=False, server_default=sa.text("'active'"), comment='active, paused, completed, abandoned'),
        sa.Column('progress_percentage', sa.Integer, nullable=False, server_default=sa.text('0'), comment='Процент выполнения плана'),
        sa.Column('schedule_type', sa.String(20), nullable=True, comment='daily, weekly, custom'),
        sa.Column('schedule_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_need_plan_user'),
        sa.ForeignKeyConstraint(['user_need_id'], ['user_needs.id'], name='fk_need_plan_user_need', ondelete='CASCADE'),
        sa.Index('ix_need_fulfillment_plans_user_id', 'user_id'),
        sa.Index('ix_need_fulfillment_plans_user_need_id', 'user_need_id'),
        sa.Index('ix_need_fulfillment_plans_status', 'status')
    )
    
    # 5. Создаем таблицу для конкретных целей в плане удовлетворения потребностей
    op.create_table(
        'need_fulfillment_objectives',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('activity_id', postgresql.UUID(as_uuid=True), nullable=True, comment='Связанная активность, если есть'),
        sa.Column('due_date', sa.Date, nullable=True),
        sa.Column('priority', sa.Integer, nullable=False, server_default=sa.text('1'), comment='Приоритет цели (1-5)'),
        sa.Column('status', sa.String(20), nullable=False, server_default=sa.text("'pending'"), comment='pending, in_progress, completed, skipped'),
        sa.Column('completion_date', sa.DateTime, nullable=True),
        sa.Column('success_criteria', sa.Text, nullable=True, comment='Критерии успешного выполнения'),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['plan_id'], ['need_fulfillment_plans.id'], name='fk_objective_plan', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['activity_id'], ['activities.id'], name='fk_objective_activity'),
        sa.Index('ix_need_fulfillment_objectives_plan_id', 'plan_id'),
        sa.Index('ix_need_fulfillment_objectives_activity_id', 'activity_id'),
        sa.Index('ix_need_fulfillment_objectives_status', 'status'),
        sa.Index('ix_need_fulfillment_objectives_due_date', 'due_date'),
        sa.Index('ix_need_fulfillment_objectives_priority', 'priority')
    )
    
    # 6. Создаем таблицу рекомендаций по улучшению удовлетворения потребностей
    op.create_table(
        'need_recommendations',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('need_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('activity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('description', sa.Text, nullable=False, comment='Описание рекомендации'),
        sa.Column('rationale', sa.Text, nullable=True, comment='Обоснование рекомендации'),
        sa.Column('priority', sa.Integer, nullable=False, server_default=sa.text('1'), comment='Приоритет рекомендации (1-5)'),
        sa.Column('status', sa.String(20), nullable=False, server_default=sa.text("'new'"), comment='new, viewed, accepted, rejected, completed'),
        sa.Column('is_ai_generated', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('source', sa.String(50), nullable=True, comment='Источник рекомендации'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_need_recommendation_user'),
        sa.ForeignKeyConstraint(['need_id'], ['needs.id'], name='fk_need_recommendation_need'),
        sa.ForeignKeyConstraint(['activity_id'], ['activities.id'], name='fk_need_recommendation_activity'),
        sa.Index('ix_need_recommendations_user_id', 'user_id'),
        sa.Index('ix_need_recommendations_need_id', 'need_id'),
        sa.Index('ix_need_recommendations_activity_id', 'activity_id'),
        sa.Index('ix_need_recommendations_status', 'status'),
        sa.Index('ix_need_recommendations_priority', 'priority')
    )


def downgrade() -> None:
    """
    Удаляет созданные таблицы потребностей в обратном порядке.
    """
    # Удаляем таблицы в обратном порядке, чтобы избежать ошибок с внешними ключами
    op.drop_table('need_recommendations')
    op.drop_table('need_fulfillment_objectives')
    op.drop_table('need_fulfillment_plans')
    op.drop_table('user_need_history')
    op.drop_table('user_needs')
    
    # Проверяем, была ли создана таблица activity_need_links
    connection = op.get_bind()
    metadata = sa.MetaData()
    metadata.reflect(bind=connection, only=['activity_need_links'])
    
    if 'activity_need_links' in metadata.tables:
        op.drop_table('activity_need_links')