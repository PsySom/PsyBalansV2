"""Create calendar and scheduling tables

Revision ID: 004_create_calendar_tables
Revises: 003_create_needs_tables
Create Date: 2025-05-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004_create_calendar_tables'
down_revision: Union[str, None] = '003_create_needs_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Создает таблицы для календаря и расписания:
    - user_calendars - календари пользователя
    - activity_schedules - запланированные активности
    - user_states - состояния пользователя
    """
    # 1. Создаем таблицу календарей пользователя
    op.create_table(
        'user_calendars',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('color', sa.String(20), nullable=True),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('is_default', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('is_primary', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('is_visible', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('is_public', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('external_id', sa.String(255), nullable=True, comment='ID календаря в внешней системе, если синхронизирован'),
        sa.Column('external_source', sa.String(50), nullable=True, comment='Источник внешнего календаря (Google, Apple, etc.)'),
        sa.Column('external_url', sa.String(255), nullable=True),
        sa.Column('sync_status', sa.String(20), nullable=True),
        sa.Column('last_synced', sa.DateTime, nullable=True),
        sa.Column('timezone', sa.String(50), nullable=True, server_default=sa.text("'UTC'")),
        sa.Column('display_order', sa.Integer, nullable=False, server_default=sa.text('100')),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_calendar_user'),
        sa.Index('ix_user_calendars_user_id', 'user_id'),
        sa.Index('ix_user_calendars_is_default', 'is_default'),
        sa.Index('ix_user_calendars_external_id', 'external_id')
    )
    
    # 2. Создаем таблицу расписания активностей
    op.create_table(
        'activity_schedules',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('calendar_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('activity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('all_day', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('color', sa.String(20), nullable=True),
        sa.Column('recurrence_rule', sa.String(255), nullable=True, comment='iCalendar RRULE формат для повторяющихся событий'),
        sa.Column('recurrence_exception_dates', postgresql.ARRAY(sa.DateTime(timezone=True)), nullable=True),
        sa.Column('recurrence_id', postgresql.UUID(as_uuid=True), nullable=True, comment='ID оригинального события для исключений'),
        sa.Column('status', sa.String(20), nullable=False, server_default=sa.text("'scheduled'"), comment='scheduled, cancelled, completed, postponed'),
        sa.Column('priority', sa.Integer, nullable=False, server_default=sa.text('3'), comment='Приоритет от 1 (высокий) до 5 (низкий)'),
        sa.Column('is_flexible', sa.Boolean, nullable=False, server_default=sa.text('false'), comment='Может ли время быть изменено'),
        sa.Column('buffer_before', sa.Integer, nullable=True, comment='Буферное время до активности в минутах'),
        sa.Column('buffer_after', sa.Integer, nullable=True, comment='Буферное время после активности в минутах'),
        sa.Column('reminder_times', postgresql.ARRAY(sa.Integer), nullable=True, comment='Минуты до начала для оповещений'),
        sa.Column('external_id', sa.String(255), nullable=True, comment='ID события в внешней системе, если синхронизировано'),
        sa.Column('external_source', sa.String(50), nullable=True),
        sa.Column('completion_status', sa.String(20), nullable=True, comment='not_started, in_progress, completed, skipped'),
        sa.Column('completion_time', sa.DateTime, nullable=True),
        sa.Column('completion_percentage', sa.Integer, nullable=True),
        sa.Column('linked_plan_objective_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('energy_required', sa.Integer, nullable=True, comment='Ожидаемые затраты энергии (1-10)'),
        sa.Column('preferred_energy_level', sa.Integer, nullable=True, comment='Предпочтительный уровень энергии (1-10)'),
        sa.Column('preferred_mood_level', sa.Integer, nullable=True, comment='Предпочтительный уровень настроения (1-10)'),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_schedule_user'),
        sa.ForeignKeyConstraint(['calendar_id'], ['user_calendars.id'], name='fk_schedule_calendar'),
        sa.ForeignKeyConstraint(['activity_id'], ['activities.id'], name='fk_schedule_activity'),
        sa.ForeignKeyConstraint(['linked_plan_objective_id'], ['need_fulfillment_objectives.id'], name='fk_schedule_objective'),
        sa.ForeignKeyConstraint(['recurrence_id'], ['activity_schedules.id'], name='fk_schedule_recurrence'),
        sa.Index('ix_activity_schedules_user_id', 'user_id'),
        sa.Index('ix_activity_schedules_calendar_id', 'calendar_id'),
        sa.Index('ix_activity_schedules_activity_id', 'activity_id'),
        sa.Index('ix_activity_schedules_start_time', 'start_time'),
        sa.Index('ix_activity_schedules_end_time', 'end_time'),
        sa.Index('ix_activity_schedules_status', 'status'),
        sa.Index('ix_activity_schedules_recurrence_id', 'recurrence_id'),
        sa.Index('ix_activity_schedules_external_id', 'external_id')
    )
    
    # 3. Создаем таблицу состояний пользователя
    op.create_table(
        'user_states',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('timestamp', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.Column('date', sa.Date, nullable=False, server_default=sa.text('current_date')),
        sa.Column('entry_type', sa.String(20), nullable=False, comment='manual, scheduled, inferred'),
        sa.Column('mood_level', sa.Integer, nullable=True, comment='Уровень настроения (-10 до +10)'),
        sa.Column('energy_level', sa.Integer, nullable=True, comment='Уровень энергии (-10 до +10)'),
        sa.Column('stress_level', sa.Integer, nullable=True, comment='Уровень стресса (0-10)'),
        sa.Column('anxiety_level', sa.Integer, nullable=True, comment='Уровень тревоги (0-10)'),
        sa.Column('focus_level', sa.Integer, nullable=True, comment='Уровень концентрации (0-10)'),
        sa.Column('physical_well_being', sa.Integer, nullable=True, comment='Физическое состояние (0-10)'),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('activity_context', sa.String(100), nullable=True, comment='Чем занимался в момент оценки'),
        sa.Column('social_context', sa.String(100), nullable=True, comment='С кем был в момент оценки'),
        sa.Column('weather_conditions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('emotions', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('physical_symptoms', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('need_satisfaction', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Оценки удовлетворенности потребностей'),
        sa.Column('related_activities', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_state_user'),
        sa.Index('ix_user_states_user_id', 'user_id'),
        sa.Index('ix_user_states_timestamp', 'timestamp'),
        sa.Index('ix_user_states_date', 'date'),
        sa.Index('ix_user_states_mood_level', 'mood_level'),
        sa.Index('ix_user_states_energy_level', 'energy_level')
    )
    
    # 4. Создаем таблицу для рекомендаций на основе состояния пользователя
    op.create_table(
        'state_based_recommendations',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('state_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('activity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('need_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('recommendation_type', sa.String(50), nullable=False, comment='activity, need, rest, social, etc.'),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('rationale', sa.Text, nullable=True, comment='Обоснование рекомендации'),
        sa.Column('priority', sa.Integer, nullable=False, server_default=sa.text('3'), comment='Приоритет от 1 (высокий) до 5 (низкий)'),
        sa.Column('status', sa.String(20), nullable=False, server_default=sa.text("'new'"), comment='new, viewed, accepted, rejected, completed'),
        sa.Column('expires_at', sa.DateTime, nullable=True),
        sa.Column('is_ai_generated', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_state_recommendation_user'),
        sa.ForeignKeyConstraint(['state_id'], ['user_states.id'], name='fk_state_recommendation_state'),
        sa.ForeignKeyConstraint(['activity_id'], ['activities.id'], name='fk_state_recommendation_activity'),
        sa.ForeignKeyConstraint(['need_id'], ['needs.id'], name='fk_state_recommendation_need'),
        sa.Index('ix_state_based_recommendations_user_id', 'user_id'),
        sa.Index('ix_state_based_recommendations_state_id', 'state_id'),
        sa.Index('ix_state_based_recommendations_activity_id', 'activity_id'),
        sa.Index('ix_state_based_recommendations_need_id', 'need_id'),
        sa.Index('ix_state_based_recommendations_status', 'status'),
        sa.Index('ix_state_based_recommendations_priority', 'priority')
    )
    
    # 5. Создаем таблицу для отслеживания блоков времени
    op.create_table(
        'time_blocks',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('calendar_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('block_type', sa.String(50), nullable=False, comment='work, rest, family, sleep, commute, etc.'),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('all_day', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('color', sa.String(20), nullable=True),
        sa.Column('recurrence_rule', sa.String(255), nullable=True),
        sa.Column('recurrence_exception_dates', postgresql.ARRAY(sa.DateTime(timezone=True)), nullable=True),
        sa.Column('recurrence_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('energy_level_expected', sa.Integer, nullable=True, comment='Ожидаемый уровень энергии (-10 до +10)'),
        sa.Column('mood_level_expected', sa.Integer, nullable=True, comment='Ожидаемый уровень настроения (-10 до +10)'),
        sa.Column('is_flexible', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('is_protected', sa.Boolean, nullable=False, server_default=sa.text('false'), comment='Не предлагать активности в это время'),
        sa.Column('priority', sa.Integer, nullable=False, server_default=sa.text('3')),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_time_block_user'),
        sa.ForeignKeyConstraint(['calendar_id'], ['user_calendars.id'], name='fk_time_block_calendar'),
        sa.ForeignKeyConstraint(['recurrence_id'], ['time_blocks.id'], name='fk_time_block_recurrence'),
        sa.Index('ix_time_blocks_user_id', 'user_id'),
        sa.Index('ix_time_blocks_calendar_id', 'calendar_id'),
        sa.Index('ix_time_blocks_start_time', 'start_time'),
        sa.Index('ix_time_blocks_end_time', 'end_time'),
        sa.Index('ix_time_blocks_block_type', 'block_type'),
        sa.Index('ix_time_blocks_recurrence_id', 'recurrence_id')
    )


def downgrade() -> None:
    """
    Удаляет созданные таблицы календаря и расписания в обратном порядке.
    """
    # Удаляем таблицы в обратном порядке, чтобы избежать ошибок с внешними ключами
    op.drop_table('time_blocks')
    op.drop_table('state_based_recommendations')
    op.drop_table('user_states')
    op.drop_table('activity_schedules')
    op.drop_table('user_calendars')