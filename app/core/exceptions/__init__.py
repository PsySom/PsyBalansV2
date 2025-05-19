"""
Пакет исключений для приложения PsyBalans.

Содержит иерархию классов исключений для различных компонентов системы,
таких как базы данных, внешние API и бизнес-логика.
"""

# Импорт исключений для работы с базами данных
from app.core.exceptions.database import (
    DatabaseError,
    ConnectionError,
    QueryError,
    ValidationError,
    IntegrityError,
    NotFoundError,
    DuplicateError,
    TransactionError
)

# Экспорт всех классов исключений
__all__ = [
    # Исключения для работы с базами данных
    "DatabaseError",
    "ConnectionError",
    "QueryError",
    "ValidationError",
    "IntegrityError",
    "NotFoundError",
    "DuplicateError",
    "TransactionError"
]