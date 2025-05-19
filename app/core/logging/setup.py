"""
Модуль для настройки и инициализации системы логирования.
"""
import logging
import logging.config
import os
import sys
from typing import Any, Dict, List, Optional, Union

from app.config import settings
from app.core.logging.json_formatter import JsonFormatter
from app.core.logging.context_logger import ContextLogger


def configure_logging(
    log_level: str = "INFO",
    json_format: bool = True,
    log_file: Optional[str] = None,
    console_output: bool = True,
    additional_fields: Optional[Dict[str, Any]] = None
) -> None:
    """
    Настраивает систему логирования с указанными параметрами.
    
    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Использовать ли JSON формат для логов
        log_file: Путь к файлу лога (если None, запись в файл не выполняется)
        console_output: Выводить ли логи в консоль
        additional_fields: Дополнительные поля для всех логов
    """
    # Настройка корневого логгера
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Удаляем существующие обработчики
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Создаем и настраиваем обработчики
    handlers = []
    
    # Консольный обработчик
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        
        if json_format:
            formatter = JsonFormatter(
                additional_fields=additional_fields or {
                    "app_name": settings.APP_NAME,
                    "app_version": settings.APP_VERSION,
                    "environment": "development" if settings.DEBUG else "production"
                }
            )
        else:
            formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s"
            )
        
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)
    
    # Файловый обработчик
    if log_file:
        # Создаем директорию для лога, если она не существует
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        
        if json_format:
            formatter = JsonFormatter(
                additional_fields=additional_fields or {
                    "app_name": settings.APP_NAME,
                    "app_version": settings.APP_VERSION,
                    "environment": "development" if settings.DEBUG else "production"
                }
            )
        else:
            formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s"
            )
        
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Добавляем обработчики к корневому логгеру
    for handler in handlers:
        root_logger.addHandler(handler)
    
    # Инициализируем ContextLogger
    ContextLogger.get_instance(level=getattr(logging, log_level.upper()))
    
    # Логируем информацию о запуске
    logging.info(
        f"Система логирования инициализирована с уровнем {log_level}"
        f", формат {'JSON' if json_format else 'TEXT'}"
    )


def get_logger(
    name: str,
    **context
) -> logging.LoggerAdapter:
    """
    Создает и возвращает логгер с указанным именем и контекстом.
    
    Args:
        name: Имя логгера
        **context: Контекстные данные для логгера
        
    Returns:
        LoggerAdapter с указанным контекстом
    """
    logger = ContextLogger.get_instance(logger_name=name)
    
    if context:
        return logger.with_context(**context)
    else:
        return logging.LoggerAdapter(logger.logger, {})


def configure_from_settings():
    """
    Настраивает систему логирования из настроек приложения.
    """
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    json_format = os.environ.get("LOG_FORMAT", "json").lower() == "json"
    log_file = os.environ.get("LOG_FILE")
    console_output = os.environ.get("LOG_CONSOLE", "true").lower() == "true"
    
    configure_logging(
        log_level=log_level,
        json_format=json_format,
        log_file=log_file,
        console_output=console_output
    )