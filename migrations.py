#!/usr/bin/env python3
"""
Удобный скрипт для управления миграциями Alembic.
Позволяет выполнять основные операции с миграциями без запоминания команд Alembic.
"""
import argparse
import os
import subprocess
import sys
from datetime import datetime

# Корректный путь к интерпретатору Python для активированного окружения
PYTHON = sys.executable
# Путь к исполняемому файлу Alembic
ALEMBIC = os.path.join(os.path.dirname(PYTHON), "alembic")

def run_command(cmd, description=None):
    """Запускает команду и выводит ее результат."""
    if description:
        print(f"\n{description}...")
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    
    if result.returncode != 0:
        print(f"Error (code {result.returncode}):")
        print(result.stderr)
        sys.exit(result.returncode)
    
    return result

def create_performance_indexes():
    """
    Создает миграцию для добавления оптимизационных индексов в базу данных.
    """
    print("Creating migration for performance indexes...")
    
    # Путь к файлу миграции
    revision_id = "005_add_performance_indexes"
    migration_file = f"alembic/versions/{revision_id}.py"
    
    # Получаем текущую ревизию для down_revision
    result = run_command([ALEMBIC, "current"], "Getting current revision")
    current_revision = result.stdout.strip().split()[0]
    
    # Формируем содержимое файла миграции
    migration_content = generate_index_migration_content(revision_id, current_revision)
    
    with open(migration_file, "w") as f:
        f.write(migration_content)
    
    print(f"Created performance indexes migration at {migration_file}")
    return 0


def generate_index_migration_content(revision_id, down_revision):
    """Генерирует содержимое файла миграции для индексов."""
    create_date = datetime.now().strftime("%Y-%m-%d")
    
    return f'''"""Add performance indexes

Revision ID: {revision_id}
Revises: {down_revision}
Create Date: {create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '{revision_id}'
down_revision: Union[str, None] = '{down_revision}'
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
    op.create_index('ix_users_name_combined', 'users', [sa.text('lower(first_name || \\' \\' || last_name)')])

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
    # user_calendars (дополнительные индексы)
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
'''


def main():
    """Основная функция для обработки аргументов командной строки."""
    parser = argparse.ArgumentParser(description="Alembic Migration Manager")
    
    subparsers = parser.add_subparsers(dest="command", help="Migration command")
    
    # Команда создания миграции
    create_parser = subparsers.add_parser("create", help="Create a new migration")
    create_parser.add_argument("--name", "-n", required=True, help="Migration name")
    create_parser.add_argument("--autogenerate", "-a", action="store_true", 
                               help="Autogenerate migration based on model changes")
    
    # Команда обновления до последней версии
    upgrade_parser = subparsers.add_parser("upgrade", help="Upgrade to a newer version")
    upgrade_parser.add_argument("--revision", "-r", default="head", 
                               help="Revision to upgrade to (default: head)")
    
    # Команда отката
    downgrade_parser = subparsers.add_parser("downgrade", help="Downgrade to an older version")
    downgrade_parser.add_argument("--revision", "-r", required=True, 
                                 help="Revision to downgrade to (use 'base' for initial state)")
    
    # Команда просмотра истории миграций
    subparsers.add_parser("history", help="Show migration history")
    
    # Команда проверки текущей версии
    subparsers.add_parser("current", help="Show current migration version")
    
    # Команда просмотра миграций для изменений моделей без применения
    subparsers.add_parser("check", help="Check what migrations would be generated (don't create files)")
    
    # Команда создания индексов производительности
    subparsers.add_parser("create_indexes", help="Create a migration with performance indexes")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Обработка различных команд
    if args.command == "create":
        cmd = [ALEMBIC, "revision"]
        if args.autogenerate:
            cmd.append("--autogenerate")
        cmd.extend(["--message", args.name])
        run_command(cmd, "Creating migration")
        
    elif args.command == "upgrade":
        run_command([ALEMBIC, "upgrade", args.revision], 
                   f"Upgrading to {args.revision}")
        
    elif args.command == "downgrade":
        run_command([ALEMBIC, "downgrade", args.revision], 
                   f"Downgrading to {args.revision}")
        
    elif args.command == "history":
        run_command([ALEMBIC, "history", "--verbose"], 
                   "Migration history")
        
    elif args.command == "current":
        run_command([ALEMBIC, "current"], 
                   "Current migration")
        
    elif args.command == "check":
        run_command([ALEMBIC, "revision", "--autogenerate", "--sql"], 
                   "Checking potential migrations")
                   
    elif args.command == "create_indexes":
        create_performance_indexes()

if __name__ == "__main__":
    main()