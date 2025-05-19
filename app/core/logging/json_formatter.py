"""
Модуль, содержащий классы для структурированного логирования в формате JSON.
"""
import datetime
import json
import logging
import socket
import sys
import traceback
import uuid
from typing import Any, Dict, List, Optional, Union


class JsonFormatter(logging.Formatter):
    """
    Форматтер для вывода логов в формате JSON.
    
    Каждая запись лога преобразуется в JSON-объект с стандартными полями:
    - timestamp: Время события в ISO 8601 формате
    - level: Уровень логгирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - logger: Имя логгера
    - message: Сообщение лога
    - module: Модуль, из которого произошло логгирование
    - line: Номер строки
    - function: Функция, в которой произошло логгирование
    - process: ID процесса
    - thread: ID потока
    - hostname: Имя хоста
    
    При наличии исключения добавляются дополнительные поля:
    - exception: Тип исключения
    - exception_message: Сообщение исключения
    - traceback: Трассировка стека
    
    Дополнительные пользовательские поля могут быть добавлены в extra при
    вызове функций логгера.
    """
    
    def __init__(
        self,
        include_traceback: bool = True,
        exclude_fields: Optional[List[str]] = None,
        additional_fields: Optional[Dict[str, Any]] = None,
        timestamp_format: str = "%Y-%m-%dT%H:%M:%S.%fZ",
    ):
        """
        Инициализирует JSON форматтер с настраиваемыми параметрами.
        
        Args:
            include_traceback: Включать ли трассировку стека при исключениях
            exclude_fields: Список полей, которые не должны включаться в вывод
            additional_fields: Дополнительные статические поля для всех логов
            timestamp_format: Формат временной метки
        """
        super().__init__()
        self.include_traceback = include_traceback
        self.exclude_fields = exclude_fields or []
        self.additional_fields = additional_fields or {}
        self.timestamp_format = timestamp_format
        self.hostname = socket.gethostname()
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Форматирует запись лога в JSON строку.
        
        Args:
            record: Запись лога для форматирования
            
        Returns:
            Строка в формате JSON с информацией из записи лога
        """
        log_data = self._prepare_log_data(record)
        
        # Добавляем дополнительные поля из extra
        self._add_extra_fields(record, log_data)
        
        # Обрабатываем исключения, если они есть
        if record.exc_info:
            self._add_exception_info(record, log_data)
        
        # Удаляем исключенные поля
        for field in self.exclude_fields:
            if field in log_data:
                del log_data[field]
        
        # Преобразуем в JSON строку
        try:
            return json.dumps(log_data, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            # В случае ошибки сериализации возвращаем упрощенную версию
            return json.dumps({
                "timestamp": datetime.datetime.utcnow().strftime(self.timestamp_format),
                "level": "ERROR",
                "message": f"Ошибка форматирования лога: {str(e)}",
                "original_message": str(record.message)
            })
    
    def _prepare_log_data(self, record: logging.LogRecord) -> Dict[str, Any]:
        """
        Подготавливает базовые данные лога.
        
        Args:
            record: Запись лога
            
        Returns:
            Словарь с базовыми полями лога
        """
        # Базовые поля лога
        log_data = {
            "timestamp": datetime.datetime.fromtimestamp(record.created).strftime(self.timestamp_format),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
            "function": record.funcName,
            "process": record.process,
            "thread": record.thread,
            "hostname": self.hostname,
        }
        
        # Добавляем дополнительные статические поля
        log_data.update(self.additional_fields)
        
        return log_data
    
    def _add_extra_fields(self, record: logging.LogRecord, log_data: Dict[str, Any]) -> None:
        """
        Добавляет дополнительные поля из атрибута extra записи лога.
        
        Args:
            record: Запись лога
            log_data: Словарь с данными лога для дополнения
        """
        # Получаем все атрибуты записи лога и исключаем стандартные
        standard_attrs = {
            'args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename',
            'funcName', 'levelname', 'levelno', 'lineno', 'module', 'msecs',
            'message', 'msg', 'name', 'pathname', 'process', 'processName',
            'relativeCreated', 'stack_info', 'thread', 'threadName'
        }
        
        # Добавляем все нестандартные атрибуты в категорию extra
        extra_fields = {}
        for attr, value in record.__dict__.items():
            if attr not in standard_attrs:
                try:
                    # Проверяем, что значение можно сериализовать в JSON
                    json.dumps({attr: value})
                    extra_fields[attr] = value
                except (TypeError, ValueError):
                    # Если значение не сериализуемо, преобразуем его в строку
                    extra_fields[attr] = str(value)
        
        if extra_fields:
            log_data["extra"] = extra_fields
    
    def _add_exception_info(self, record: logging.LogRecord, log_data: Dict[str, Any]) -> None:
        """
        Добавляет информацию об исключении в данные лога.
        
        Args:
            record: Запись лога с информацией об исключении
            log_data: Словарь с данными лога для дополнения
        """
        exc_type, exc_value, exc_tb = record.exc_info
        
        exception_data = {
            "exception": exc_type.__name__,
            "exception_message": str(exc_value),
        }
        
        if self.include_traceback and exc_tb:
            # Форматируем трассировку стека без заголовка и footer
            tb_lines = traceback.format_exception(exc_type, exc_value, exc_tb)
            exception_data["traceback"] = "".join(tb_lines).strip()
            
        log_data["exception_data"] = exception_data