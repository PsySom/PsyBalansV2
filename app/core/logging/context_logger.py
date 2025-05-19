"""
Модуль, содержащий классы для контекстно-зависимого логирования.
"""
import copy
import logging
import threading
from contextvars import ContextVar
from logging import Logger, LoggerAdapter
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, cast, Callable
from uuid import UUID

# TypeVar для методов класса
T = TypeVar('T', bound='ContextLogger')


# Контекстная переменная для хранения информации о запросе и пользователе
_request_context: ContextVar[Dict[str, Any]] = ContextVar('request_context', default={})


class ContextLoggerAdapter(LoggerAdapter):
    """
    Адаптер логгера, добавляющий контекстную информацию к записям лога.
    """
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        """
        Обрабатывает сообщение, добавляя контекстную информацию из адаптера.
        
        Args:
            msg: Сообщение лога
            kwargs: Дополнительные аргументы для функции логгирования
            
        Returns:
            Кортеж (сообщение, обновленные kwargs) для дальнейшей обработки
        """
        # Создаем копию текущего контекста
        extra = kwargs.get('extra', {}).copy()
        
        # Добавляем контекст из адаптера
        if self.extra:
            for key, value in self.extra.items():
                if key not in extra:
                    extra[key] = value
        
        # Добавляем глобальный контекст запроса
        request_context = _request_context.get()
        if request_context:
            for key, value in request_context.items():
                if key not in extra:
                    extra[key] = value
        
        # Обновляем kwargs
        kwargs['extra'] = extra
        return msg, kwargs


class ContextLogger:
    """
    Логгер с поддержкой контекста запроса и пользователя.
    
    Предоставляет методы для установки контекста и создания новых экземпляров
    логгера с дополнительным контекстом.
    """
    
    _instance: Optional['ContextLogger'] = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs) -> 'ContextLogger':
        """
        Реализует паттерн Singleton для ContextLogger.
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ContextLogger, cls).__new__(cls)
            return cls._instance
    
    def __init__(self, logger_name: str = "app", level: int = logging.INFO):
        """
        Инициализирует экземпляр ContextLogger.
        
        Args:
            logger_name: Имя базового логгера
            level: Уровень логгирования
        """
        # Инициализируем только один раз для паттерна Singleton
        if not hasattr(self, '_initialized'):
            self.logger = logging.getLogger(logger_name)
            self.logger.setLevel(level)
            self._initialized = True
    
    @classmethod
    def get_instance(cls, logger_name: str = "app", level: int = logging.INFO) -> 'ContextLogger':
        """
        Возвращает экземпляр ContextLogger (Singleton).
        
        Args:
            logger_name: Имя базового логгера
            level: Уровень логгирования
            
        Returns:
            Экземпляр ContextLogger
        """
        return cls(logger_name, level)
    
    @classmethod
    def set_context(cls, **context) -> None:
        """
        Устанавливает глобальный контекст для всех логгеров.
        
        Args:
            **context: Ключи и значения контекста
        """
        current_context = _request_context.get().copy()
        current_context.update(context)
        _request_context.set(current_context)
    
    @classmethod
    def clear_context(cls) -> None:
        """
        Очищает глобальный контекст.
        """
        _request_context.set({})
    
    def with_context(self, **context) -> LoggerAdapter:
        """
        Создает новый адаптер логгера с дополнительным контекстом.
        
        Args:
            **context: Ключи и значения контекста
            
        Returns:
            LoggerAdapter с указанным контекстом
        """
        return ContextLoggerAdapter(self.logger, context)
    
    def get_with_request_id(self, request_id: str) -> LoggerAdapter:
        """
        Создает логгер с ID запроса.
        
        Args:
            request_id: Идентификатор запроса
            
        Returns:
            LoggerAdapter с ID запроса
        """
        return self.with_context(request_id=request_id)
    
    def get_with_user_id(self, user_id: Union[str, UUID]) -> LoggerAdapter:
        """
        Создает логгер с ID пользователя.
        
        Args:
            user_id: Идентификатор пользователя
            
        Returns:
            LoggerAdapter с ID пользователя
        """
        return self.with_context(user_id=str(user_id))
    
    def get_with_user_and_request(self, user_id: Union[str, UUID], request_id: str) -> LoggerAdapter:
        """
        Создает логгер с ID пользователя и запроса.
        
        Args:
            user_id: Идентификатор пользователя
            request_id: Идентификатор запроса
            
        Returns:
            LoggerAdapter с ID пользователя и запроса
        """
        return self.with_context(user_id=str(user_id), request_id=request_id)
    
    # Делегируем стандартные методы логгирования базовому логгеру
    
    def debug(self, msg: str, *args, **kwargs) -> None:
        """Логирует сообщение с уровнем DEBUG."""
        self.logger.debug(msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs) -> None:
        """Логирует сообщение с уровнем INFO."""
        self.logger.info(msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs) -> None:
        """Логирует сообщение с уровнем WARNING."""
        self.logger.warning(msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs) -> None:
        """Логирует сообщение с уровнем ERROR."""
        self.logger.error(msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs) -> None:
        """Логирует сообщение с уровнем CRITICAL."""
        self.logger.critical(msg, *args, **kwargs)
    
    def exception(self, msg: str, *args, **kwargs) -> None:
        """Логирует сообщение с уровнем ERROR, включая информацию об исключении."""
        self.logger.exception(msg, *args, **kwargs)
    
    def log(self, level: int, msg: str, *args, **kwargs) -> None:
        """Логирует сообщение с указанным уровнем."""
        self.logger.log(level, msg, *args, **kwargs)