"""Add performance indexes

Revision ID: 005_add_performance_indexes
Revises: 004_create_calendar_tables
Create Date: 2025-05-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '005_add_performance_indexes'
down_revision: Union[str, None] = '004_create_calendar_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Добавляет оптимизационные индексы для наиболее часто используемых 
    полей в ключевых таблицах.
    """
    # 1. Индексы для таблицы пользователей
    op.create_index('ix_users_email_lower', 'users', [sa.text('lower(email)')], unique=True)
    op.create_index('ix_users_first_name', 'users', ['first_name'])
    op.create_index('ix_users_last_name', 'users', ['last_name'])
    op.create_index('ix_users_is_active', 'users', ['is_active'])
    op.create_index('ix_users_name_combined', 'users', [sa.text('lower(first_name || \' \' || last_name)')])

    # 2. Индексы для таблиц активностей
    op.create_index('ix_activities_type_id', 'activities', ['activity_type_id'])
    op.create_index('ix_activities_subtype_id', 'activities', ['activity_subtype_id'])
    op.create_index('ix_activities_energy_required', 'activities', ['energy_required'])
    op.create_index('ix_activities_is_restorative', 'activities', ['is_restorative'])
    op.create_index('ix_activities_difficulty', 'activities', ['difficulty'])
    
    # Составной индекс для поиска деятельности по типу+подтипу
    op.create_index('ix_activities_type_subtype', 'activities', 
                     ['activity_type_id', 'activity_subtype_id'])
    
    # Индексы для типов активностей
    op.create_index('ix_activity_types_name', 'activity_types', [sa.text('lower(name)')])
    op.create_index('ix_activity_subtypes_name', 'activity_subtypes', [sa.text('lower(name)')])
    op.create_index('ix_activity_subtypes_type_id', 'activity_subtypes', ['activity_type_id'])

    # 3. Индексы для таблиц календаря
    # user_calendars (основные индексы уже добавлены в миграции создания таблицы)
    op.create_index('ix_user_calendars_is_visible', 'user_calendars', ['is_visible'])
    
    # Составной индекс для активного календаря пользователя
    op.create_index('ix_user_calendars_user_visible', 'user_calendars', 
                     ['user_id', 'is_visible'])
    
    # activity_schedules (дополнительные индексы)
    # Индекс для быстрого поиска расписания пользователя в определенном временном интервале
    op.create_index('ix_activity_schedules_user_time_range', 'activity_schedules', 
                     ['user_id', 'start_time', 'end_time'])
    
    # Индекс для быстрого поиска расписания по статусу
    op.create_index('ix_activity_schedules_user_status', 'activity_schedules', 
                     ['user_id', 'status'])
    
    # Индекс для неоконченных мероприятий (предстоящих или в процессе)
    op.create_index('ix_activity_schedules_pending', 'activity_schedules', 
                     ['user_id', 'status', 'start_time'],
                     postgresql_where=sa.text("status IN ('scheduled', 'in_progress')"))
    
    # 4. Индексы для таблиц потребностей
    # Основная таблица потребностей
    op.create_index('ix_needs_category_id', 'needs', ['category_id'])
    
    # Индекс для таблицы категорий потребностей
    op.create_index('ix_need_categories_name', 'need_categories', [sa.text('lower(name)')])
    op.create_index('ix_need_categories_display_order', 'need_categories', ['display_order'])
    
    # Индексы для таблицы пользовательских потребностей
    op.create_index('ix_user_needs_satisfaction', 'user_needs', ['current_satisfaction'])
    op.create_index('ix_user_needs_importance', 'user_needs', ['importance'])
    
    # Составной индекс для быстрого поиска неудовлетворенных потребностей конкретного пользователя
    op.create_index('ix_user_needs_user_low_satisfaction', 'user_needs', 
                     ['user_id', 'current_satisfaction'],
                     postgresql_where=sa.text("current_satisfaction < 0"))
    
    # Индекс для быстрого поиска важных потребностей пользователя
    op.create_index('ix_user_needs_user_high_importance', 'user_needs', 
                     ['user_id', 'importance'],
                     postgresql_where=sa.text("importance > 0.7"))
    
    # Полнотекстовый GIN-индекс для поиска потребностей по описанию
    op.execute("""
        CREATE INDEX ix_needs_description_tsvector ON needs 
        USING GIN (to_tsvector('russian', coalesce(description, '')))
    """)
    
    # Создаем триггер для обновления полнотекстового индекса
    op.execute("""
        CREATE TRIGGER needs_description_trigger 
        BEFORE INSERT OR UPDATE ON needs 
        FOR EACH ROW EXECUTE FUNCTION 
        tsvector_update_trigger(description_tsv, 'pg_catalog.russian', description)
    """)


def downgrade() -> None:
    """
    Удаляет созданные индексы в обратном порядке.
    """
    # 1. Удаление индексов таблицы пользователей
    op.drop_index('ix_users_email_lower', table_name='users')
    op.drop_index('ix_users_first_name', table_name='users')
    op.drop_index('ix_users_last_name', table_name='users')
    op.drop_index('ix_users_is_active', table_name='users')
    op.drop_index('ix_users_name_combined', table_name='users')

    # 2. Удаление индексов таблиц активностей
    op.drop_index('ix_activities_type_id', table_name='activities')
    op.drop_index('ix_activities_subtype_id', table_name='activities')
    op.drop_index('ix_activities_energy_required', table_name='activities')
    op.drop_index('ix_activities_is_restorative', table_name='activities')
    op.drop_index('ix_activities_difficulty', table_name='activities')
    op.drop_index('ix_activities_type_subtype', table_name='activities')
    
    op.drop_index('ix_activity_types_name', table_name='activity_types')
    op.drop_index('ix_activity_subtypes_name', table_name='activity_subtypes')
    op.drop_index('ix_activity_subtypes_type_id', table_name='activity_subtypes')

    # 3. Удаление индексов таблиц календаря
    op.drop_index('ix_user_calendars_is_visible', table_name='user_calendars')
    op.drop_index('ix_user_calendars_user_visible', table_name='user_calendars')
    
    op.drop_index('ix_activity_schedules_user_time_range', table_name='activity_schedules')
    op.drop_index('ix_activity_schedules_user_status', table_name='activity_schedules')
    op.drop_index('ix_activity_schedules_pending', table_name='activity_schedules')

    # 4. Удаление индексов таблиц потребностей
    op.drop_index('ix_needs_category_id', table_name='needs')
    
    op.drop_index('ix_need_categories_name', table_name='need_categories')
    op.drop_index('ix_need_categories_display_order', table_name='need_categories')
    
    op.drop_index('ix_user_needs_satisfaction', table_name='user_needs')
    op.drop_index('ix_user_needs_importance', table_name='user_needs')
    op.drop_index('ix_user_needs_user_low_satisfaction', table_name='user_needs')
    op.drop_index('ix_user_needs_user_high_importance', table_name='user_needs')
    
    # Удаление полнотекстового индекса и триггера
    op.execute("DROP TRIGGER IF EXISTS needs_description_trigger ON needs")
    op.drop_index('ix_needs_description_tsvector', table_name='needs')