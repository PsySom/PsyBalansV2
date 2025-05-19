"""
Пакет для структурированного логирования в формате JSON и с поддержкой контекста.
"""
from app.core.logging.json_formatter import JsonFormatter
from app.core.logging.context_logger import (
    ContextLogger, ContextLoggerAdapter, _request_context
)
from app.core.logging.setup import (
    configure_logging, get_logger, configure_from_settings
)
from app.core.logging.middleware import (
    RequestLoggingMiddleware, add_logging_middleware
)

__all__ = [
    "JsonFormatter",
    "ContextLogger",
    "ContextLoggerAdapter",
    "configure_logging",
    "get_logger",
    "configure_from_settings",
    "RequestLoggingMiddleware",
    "add_logging_middleware"
]