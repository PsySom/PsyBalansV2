"""Create exercises and special activity types tables

Revision ID: 002_create_exercises_tables
Revises: 001_create_activity_tables
Create Date: 2025-05-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_create_exercises_tables'
down_revision: Union[str, None] = '001_create_activity_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Создает таблицы для специальных типов активностей:
    - exercises - упражнения
    - tests - психологические тесты
    - practices - практики
    - user_exercise_progress - прогресс пользователя в упражнениях
    """
    # 1. Создаем базовую таблицу упражнений
    op.create_table(
        'exercises',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('activity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type', sa.String(20), nullable=False, comment='Тип упражнения: test, practice, meditation, etc.'),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('instructions', sa.Text, nullable=True),
        sa.Column('benefits', sa.Text, nullable=True),
        sa.Column('duration_minutes', sa.Integer, nullable=False, comment='Примерная длительность выполнения'),
        sa.Column('difficulty_level', sa.Integer, nullable=False, server_default=sa.text('1'), comment='Сложность от 1 до 5'),
        sa.Column('recommended_frequency', sa.String(50), nullable=True, comment='Рекомендуемая частота выполнения'),
        sa.Column('prerequisites', postgresql.ARRAY(sa.String), nullable=True, comment='Предварительные требования'),
        sa.Column('tags', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('category', sa.String(50), nullable=True, comment='Категория упражнения'),
        sa.Column('content', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='Основное содержимое упражнения'),
        sa.Column('media_urls', postgresql.ARRAY(sa.String), nullable=True, comment='Ссылки на медиа-файлы'),
        sa.Column('is_featured', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('is_premium', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('is_published', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('popularity', sa.Integer, nullable=False, server_default=sa.text('0'), comment='Счетчик популярности'),
        sa.Column('success_rate', sa.Float, nullable=True, comment='Процент успешных завершений'),
        sa.Column('average_rating', sa.Float, nullable=True, comment='Средняя оценка пользователей'),
        sa.Column('version', sa.String(20), nullable=False, server_default=sa.text("'1.0'")),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('published_at', sa.DateTime, nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['activity_id'], ['activities.id'], name='fk_exercise_activity'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], name='fk_exercise_author'),
        sa.Index('ix_exercises_activity_id', 'activity_id'),
        sa.Index('ix_exercises_type', 'type'),
        sa.Index('ix_exercises_difficulty', 'difficulty_level'),
        sa.Index('ix_exercises_is_published', 'is_published'),
        sa.Index('ix_exercises_popularity', 'popularity')
    )
    
    # 2. Создаем таблицу психологических тестов
    op.create_table(
        'tests',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('exercise_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('test_type', sa.String(50), nullable=False, comment='Тип теста: personality, mood, anxiety, etc.'),
        sa.Column('questions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='Вопросы теста в структурированном формате'),
        sa.Column('scoring_algorithm', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='Алгоритм подсчета результатов'),
        sa.Column('result_interpretations', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='Интерпретации различных результатов'),
        sa.Column('time_limit_minutes', sa.Integer, nullable=True, comment='Ограничение по времени'),
        sa.Column('randomize_questions', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('allow_partial_completion', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('show_progress', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('validation_studies', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Информация о валидации теста'),
        sa.Column('references', postgresql.ARRAY(sa.String), nullable=True, comment='Научные источники'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['exercise_id'], ['exercises.id'], name='fk_test_exercise', ondelete='CASCADE'),
        sa.Index('ix_tests_exercise_id', 'exercise_id'),
        sa.Index('ix_tests_test_type', 'test_type')
    )
    
    # 3. Создаем таблицу практик
    op.create_table(
        'practices',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('exercise_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('practice_type', sa.String(50), nullable=False, comment='Тип практики: meditation, journaling, cbt, etc.'),
        sa.Column('steps', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='Шаги выполнения практики'),
        sa.Column('audio_guidance', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('audio_url', sa.String(255), nullable=True),
        sa.Column('has_timer', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('timer_settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('has_reminders', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('reminder_defaults', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('scientific_background', sa.Text, nullable=True),
        sa.Column('adaptations', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Варианты адаптации практики'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['exercise_id'], ['exercises.id'], name='fk_practice_exercise', ondelete='CASCADE'),
        sa.Index('ix_practices_exercise_id', 'exercise_id'),
        sa.Index('ix_practices_practice_type', 'practice_type')
    )
    
    # 4. Создаем таблицу для отслеживания прогресса пользователя в упражнениях
    op.create_table(
        'user_exercise_progress',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('exercise_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, comment='not_started, in_progress, completed, abandoned'),
        sa.Column('start_date', sa.DateTime, nullable=True),
        sa.Column('last_activity_date', sa.DateTime, nullable=True),
        sa.Column('completion_date', sa.DateTime, nullable=True),
        sa.Column('progress_percentage', sa.Float, nullable=False, server_default=sa.text('0'), comment='Процент завершения'),
        sa.Column('current_step', sa.Integer, nullable=False, server_default=sa.text('0')),
        sa.Column('time_spent_seconds', sa.Integer, nullable=False, server_default=sa.text('0')),
        sa.Column('attempts', sa.Integer, nullable=False, server_default=sa.text('0')),
        sa.Column('last_answers', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Последние ответы в тесте или практике'),
        sa.Column('results', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Результаты выполнения'),
        sa.Column('user_notes', sa.Text, nullable=True),
        sa.Column('rating', sa.Integer, nullable=True, comment='Оценка пользователя от 1 до 5'),
        sa.Column('favorite', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('reminders', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('next_scheduled_date', sa.DateTime, nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_progress_user'),
        sa.ForeignKeyConstraint(['exercise_id'], ['exercises.id'], name='fk_progress_exercise'),
        sa.UniqueConstraint('user_id', 'exercise_id', name='uq_user_exercise_progress'),
        sa.Index('ix_user_exercise_progress_user_id', 'user_id'),
        sa.Index('ix_user_exercise_progress_exercise_id', 'exercise_id'),
        sa.Index('ix_user_exercise_progress_status', 'status'),
        sa.Index('ix_user_exercise_progress_next_scheduled', 'next_scheduled_date')
    )
    
    # 5. Создаем таблицу для отслеживания истории выполнения упражнений
    op.create_table(
        'exercise_completion_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('exercise_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('completion_date', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.Column('duration_seconds', sa.Integer, nullable=True),
        sa.Column('success', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('answers', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('results', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('mood_before', sa.Integer, nullable=True, comment='Настроение до упражнения (1-10)'),
        sa.Column('mood_after', sa.Integer, nullable=True, comment='Настроение после упражнения (1-10)'),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_completion_user'),
        sa.ForeignKeyConstraint(['exercise_id'], ['exercises.id'], name='fk_completion_exercise'),
        sa.Index('ix_exercise_completion_history_user_id', 'user_id'),
        sa.Index('ix_exercise_completion_history_exercise_id', 'exercise_id'),
        sa.Index('ix_exercise_completion_history_date', 'completion_date')
    )
    
    # 6. Создание таблицы для рекомендаций упражнений на основе потребностей
    op.create_table(
        'exercise_need_recommendations',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('exercise_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('need_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('recommendation_strength', sa.Integer, nullable=False, comment='Сила рекомендации от 1 до 10'),
        sa.Column('conditions', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Условия, при которых рекомендация особенно уместна'),
        sa.Column('explanation', sa.Text, nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['exercise_id'], ['exercises.id'], name='fk_recommendation_exercise'),
        sa.ForeignKeyConstraint(['need_id'], ['needs.id'], name='fk_recommendation_need'),
        sa.UniqueConstraint('exercise_id', 'need_id', name='uq_exercise_need_recommendation'),
        sa.Index('ix_exercise_need_recommendations_exercise_id', 'exercise_id'),
        sa.Index('ix_exercise_need_recommendations_need_id', 'need_id'),
        sa.Index('ix_exercise_need_recommendations_strength', 'recommendation_strength')
    )


def downgrade() -> None:
    """
    Удаляет созданные таблицы упражнений в обратном порядке.
    """
    # Удаляем таблицы в обратном порядке, чтобы избежать ошибок с внешними ключами
    op.drop_table('exercise_need_recommendations')
    op.drop_table('exercise_completion_history')
    op.drop_table('user_exercise_progress')
    op.drop_table('practices')
    op.drop_table('tests')
    op.drop_table('exercises')