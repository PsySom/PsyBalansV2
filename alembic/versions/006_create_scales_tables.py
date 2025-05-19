"""
Создание таблиц для шкал самонаблюдения.

Revision ID: 006_create_scales_tables
Revises: 005_add_performance_indexes
Create Date: 2025-05-19 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid


# revision identifiers, used by Alembic.
revision = '006_create_scales_tables'
down_revision = '005_add_performance_indexes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Создаем таблицу категорий шкал
    op.create_table(
        'scale_categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('color', sa.String(20), nullable=True),
        sa.Column('order', sa.Integer, default=0, nullable=False),
        sa.Column('is_system', sa.Boolean, default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
    )
    
    # Создаем таблицу шкал самонаблюдения
    op.create_table(
        'observation_scales',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('color', sa.String(20), nullable=True),
        sa.Column('min_value', sa.Float, nullable=False),
        sa.Column('max_value', sa.Float, nullable=False),
        sa.Column('step', sa.Float, default=1.0, nullable=False),
        sa.Column('default_value', sa.Float, nullable=True),
        sa.Column('unit', sa.String(20), nullable=True),
        sa.Column('display_type', sa.String(20), default='slider', nullable=False),
        sa.Column('labels', postgresql.JSONB, nullable=True),
        sa.Column('is_inverted', sa.Boolean, default=False, nullable=False),
        sa.Column('is_required', sa.Boolean, default=False, nullable=False),
        sa.Column('is_system', sa.Boolean, default=False, nullable=False),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('alert_threshold_min', sa.Float, nullable=True),
        sa.Column('alert_threshold_max', sa.Float, nullable=True),
        sa.Column('chart_color', sa.String(20), nullable=True),
        sa.Column('chart_type', sa.String(20), default='line', nullable=False),
        sa.Column('creator_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('min_value < max_value', name='check_scale_min_less_than_max'),
    )
    
    # Создаем таблицу связи шкал с категориями
    op.create_table(
        'scale_categories_association',
        sa.Column('scale_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('observation_scales.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('scale_categories.id', ondelete='CASCADE'), primary_key=True),
    )
    
    # Создаем таблицу оценок по шкалам
    op.create_table(
        'scale_ratings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('scale_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('observation_scales.id', ondelete='CASCADE'), nullable=False),
        sa.Column('value', sa.Float, nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('activity_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('activities.id', ondelete='SET NULL'), nullable=True),
        sa.Column('activity_schedule_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('activity_schedules.id', ondelete='SET NULL'), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('context', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
    )
    
    # Создаем индексы для оптимизации запросов
    op.create_index('idx_scale_categories_name', 'scale_categories', ['name'])
    op.create_index('idx_scale_categories_order', 'scale_categories', ['order'])
    op.create_index('idx_observation_scales_name', 'observation_scales', ['name'])
    op.create_index('idx_observation_scales_creator', 'observation_scales', ['creator_id'])
    op.create_index('idx_observation_scales_system', 'observation_scales', ['is_system'])
    op.create_index('idx_scale_ratings_user', 'scale_ratings', ['user_id'])
    op.create_index('idx_scale_ratings_scale', 'scale_ratings', ['scale_id'])
    op.create_index('idx_scale_ratings_timestamp', 'scale_ratings', ['timestamp'])
    op.create_index('idx_scale_ratings_activity', 'scale_ratings', ['activity_id'])
    op.create_index('idx_scale_ratings_user_scale', 'scale_ratings', ['user_id', 'scale_id'])
    op.create_index('idx_scale_ratings_user_time', 'scale_ratings', ['user_id', 'timestamp'])
    
    # Добавляем начальные данные для системных категорий
    op.execute(
        """
        INSERT INTO scale_categories (id, name, description, icon, color, "order", is_system, created_at, updated_at, is_active)
        VALUES 
        ('2e8a0d36-a8a0-4b85-8e28-c5e2a73e09f1', 'Эмоциональные', 'Шкалы для отслеживания эмоционального состояния', 'mdi-emoticon', '#f44336', 1, true, now(), now(), true),
        ('4fbe8f3d-d1ca-4f85-9de5-5fe1cb5c7a64', 'Физические', 'Шкалы для отслеживания физического состояния', 'mdi-run', '#4caf50', 2, true, now(), now(), true),
        ('56d21fa1-3c19-4aac-9e4f-06c89e9a28ec', 'Когнитивные', 'Шкалы для отслеживания когнитивных функций', 'mdi-brain', '#2196f3', 3, true, now(), now(), true),
        ('9d7c4b55-9e53-4e1c-8bd1-7d988c33b2c1', 'Социальные', 'Шкалы для отслеживания социального взаимодействия', 'mdi-account-group', '#9c27b0', 4, true, now(), now(), true),
        ('f3a39689-f9e6-4a13-8c01-cc2bb1ed7c90', 'Духовные', 'Шкалы для отслеживания духовного состояния', 'mdi-meditation', '#ff9800', 5, true, now(), now(), true)
        """
    )
    
    # Добавляем базовые системные шкалы
    op.execute(
        """
        INSERT INTO observation_scales 
        (id, name, description, icon, color, min_value, max_value, step, default_value, display_type, 
        labels, is_inverted, is_system, chart_color, created_at, updated_at, is_active)
        VALUES 
        ('b3bd4e83-cf53-49f7-a44d-a8dbeea1b63f', 'Настроение', 'Общее настроение', 'mdi-emoticon', '#f44336', -10, 10, 1, 0, 'slider', 
        '{"min": "Очень плохое", "max": "Очень хорошее", "0": "Нейтральное"}', false, true, '#f44336', now(), now(), true),
        
        ('d1e8e7a5-7f32-4caa-b7d2-f1a2bfc2d5e5', 'Энергия', 'Уровень энергии и активности', 'mdi-battery', '#4caf50', -10, 10, 1, 0, 'slider',
        '{"min": "Полное истощение", "max": "Максимальная энергия", "0": "Средний уровень"}', false, true, '#4caf50', now(), now(), true),
        
        ('49c74c2b-cd1a-4fe0-90bc-75f4ff25e50c', 'Стресс', 'Уровень стресса и напряжения', 'mdi-alert-circle', '#ff5722', 0, 10, 1, 3, 'slider',
        '{"min": "Отсутствует", "max": "Критический", "5": "Умеренный"}', true, true, '#ff5722', now(), now(), true),
        
        ('8fd11efa-94b9-4e49-b5e8-e3a1c9d31f1e', 'Тревожность', 'Уровень тревоги', 'mdi-alert', '#ff9800', 0, 10, 1, 2, 'slider',
        '{"min": "Отсутствует", "max": "Очень сильная", "5": "Умеренная"}', true, true, '#ff9800', now(), now(), true),
        
        ('62a051af-b514-4c03-87a4-a9a5bfd9e88d', 'Концентрация', 'Способность сфокусироваться', 'mdi-target', '#2196f3', 0, 10, 1, 5, 'slider',
        '{"min": "Отсутствует", "max": "Полная концентрация", "5": "Средняя"}', false, true, '#2196f3', now(), now(), true),
        
        ('1c97d33c-4ff5-4e63-942e-25ec0f24b124', 'Качество сна', 'Качество сна прошлой ночью', 'mdi-sleep', '#9c27b0', 0, 10, 1, 5, 'slider',
        '{"min": "Очень плохое", "max": "Отличное", "5": "Среднее"}', false, true, '#9c27b0', now(), now(), true)
        """
    )
    
    # Связываем шкалы с категориями
    op.execute(
        """
        INSERT INTO scale_categories_association (scale_id, category_id) VALUES
        ('b3bd4e83-cf53-49f7-a44d-a8dbeea1b63f', '2e8a0d36-a8a0-4b85-8e28-c5e2a73e09f1'),  -- Настроение -> Эмоциональные
        ('d1e8e7a5-7f32-4caa-b7d2-f1a2bfc2d5e5', '4fbe8f3d-d1ca-4f85-9de5-5fe1cb5c7a64'),  -- Энергия -> Физические
        ('49c74c2b-cd1a-4fe0-90bc-75f4ff25e50c', '2e8a0d36-a8a0-4b85-8e28-c5e2a73e09f1'),  -- Стресс -> Эмоциональные
        ('8fd11efa-94b9-4e49-b5e8-e3a1c9d31f1e', '2e8a0d36-a8a0-4b85-8e28-c5e2a73e09f1'),  -- Тревожность -> Эмоциональные
        ('62a051af-b514-4c03-87a4-a9a5bfd9e88d', '56d21fa1-3c19-4aac-9e4f-06c89e9a28ec'),  -- Концентрация -> Когнитивные
        ('1c97d33c-4ff5-4e63-942e-25ec0f24b124', '4fbe8f3d-d1ca-4f85-9de5-5fe1cb5c7a64')   -- Качество сна -> Физические
        """
    )


def downgrade() -> None:
    # Удаляем таблицы и индексы
    op.drop_table('scale_ratings')
    op.drop_table('scale_categories_association')
    op.drop_table('observation_scales')
    op.drop_table('scale_categories')