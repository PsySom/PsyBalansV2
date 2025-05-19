"""
Middleware для логирования операций с PostgreSQL.
"""
import time
import functools
import inspect
import re
from typing import Any, Callable, Dict, List, Optional, Set, Type, TypeVar, Union, cast

from sqlalchemy.engine import Engine
from sqlalchemy.event import listen
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import ClauseElement

from app.core.logging import get_logger
from app.core.middleware.utils import sanitize_payload, truncate_payload

# Типы для декораторов
F = TypeVar('F', bound=Callable[..., Any])
T = TypeVar('T')


class DatabaseLoggerMiddleware:
    """
    Middleware для логирования операций с базой данных PostgreSQL.
    
    Отслеживает выполнение SQL-запросов, измеряет время выполнения и
    логирует детали операций в структурированном формате.
    """
    
    def __init__(
        self,
        engine: Union[Engine, AsyncEngine],
        slow_query_threshold: float = 1.0,
        log_sensitive_data: bool = False,
        log_level: str = "DEBUG"
    ):
        """
        Инициализация middleware для логирования операций с базой данных.
        
        Args:
            engine: SQLAlchemy Engine или AsyncEngine
            slow_query_threshold: Порог времени выполнения для медленных запросов (в секундах)
            log_sensitive_data: Логировать ли чувствительные данные (не рекомендуется)
            log_level: Уровень логирования (DEBUG, INFO, WARNING)
        """
        self.engine = engine
        self.slow_query_threshold = slow_query_threshold
        self.log_sensitive_data = log_sensitive_data
        self.log_level = log_level.upper()
        
        self.logger = get_logger("app.db.postgresql")
        
        # Регистрируем обработчики событий
        self._register_event_listeners()
    
    def _register_event_listeners(self) -> None:
        """
        Регистрирует обработчики событий для SQLAlchemy Engine.
        """
        # Регистрируем обработчики для синхронного или асинхронного движка
        if isinstance(self.engine, AsyncEngine):
            listen(self.engine.sync_engine, "before_cursor_execute", self._before_cursor_execute)
            listen(self.engine.sync_engine, "after_cursor_execute", self._after_cursor_execute)
            listen(self.engine.sync_engine, "handle_error", self._handle_error)
        else:
            listen(self.engine, "before_cursor_execute", self._before_cursor_execute)
            listen(self.engine, "after_cursor_execute", self._after_cursor_execute)
            listen(self.engine, "handle_error", self._handle_error)
    
    def _before_cursor_execute(
        self, 
        conn, 
        cursor, 
        statement, 
        parameters, 
        context, 
        executemany
    ) -> None:
        """
        Обработчик события перед выполнением запроса.
        
        Записывает время начала выполнения запроса и создает контекст для логирования.
        """
        # Сохраняем время начала выполнения
        conn.info.setdefault('query_start_time', {})
        conn.info['query_start_time'][id(cursor)] = time.time()
        
        # Сохраняем запрос и параметры для логирования
        conn.info.setdefault('statements', {})
        
        # Очищаем параметры от чувствительных данных, если нужно
        cleaned_parameters = parameters
        if not self.log_sensitive_data:
            if isinstance(parameters, (list, tuple)) and all(isinstance(p, dict) for p in parameters):
                # Для executemany параметры - список словарей
                cleaned_parameters = [sanitize_payload(p) for p in parameters]
            elif isinstance(parameters, dict):
                # Обычные параметры
                cleaned_parameters = sanitize_payload(parameters)
            else:
                # Другие форматы (tuple, etc.)
                cleaned_parameters = "<hidden>"
        
        # Сохраняем запрос и параметры
        conn.info['statements'][id(cursor)] = (statement, cleaned_parameters, executemany)
    
    def _after_cursor_execute(
        self, 
        conn, 
        cursor, 
        statement, 
        parameters, 
        context, 
        executemany
    ) -> None:
        """
        Обработчик события после выполнения запроса.
        
        Вычисляет время выполнения и логирует информацию о запросе.
        """
        # Получаем время начала выполнения
        start_time = conn.info['query_start_time'].pop(id(cursor), 0)
        
        if not start_time:
            return
        
        # Вычисляем продолжительность
        duration = time.time() - start_time
        
        # Получаем сохраненный запрос и параметры
        saved_statement, saved_parameters, saved_executemany = conn.info['statements'].pop(id(cursor), (None, None, None))
        
        if not saved_statement:
            return
        
        # Определяем тип операции
        operation_type = self._get_operation_type(saved_statement)
        
        # Подготавливаем контекст для логирования
        log_context = {
            "operation": operation_type,
            "duration_ms": round(duration * 1000, 2),
            "executemany": saved_executemany,
            "rows_affected": cursor.rowcount if hasattr(cursor, 'rowcount') else -1,
        }
        
        # Добавляем параметры, если они доступны
        if saved_parameters:
            log_context["parameters"] = truncate_payload(saved_parameters)
        
        # Выбираем уровень логирования в зависимости от времени выполнения
        log_message = f"{operation_type} выполнен за {log_context['duration_ms']} мс"
        
        # Сокращаем текст запроса для лога
        statement_preview = self._get_statement_preview(saved_statement)
        log_message += f": {statement_preview}"
        
        # Определяем, медленный ли запрос
        is_slow = duration >= self.slow_query_threshold
        
        # Логируем информацию о запросе
        if is_slow:
            self.logger.warning(f"SLOW QUERY: {log_message}", extra=log_context)
        elif self.log_level == "DEBUG":
            self.logger.debug(log_message, extra=log_context)
        elif self.log_level == "INFO":
            self.logger.info(log_message, extra=log_context)
    
    def _handle_error(
        self, 
        context
    ) -> None:
        """
        Обработчик ошибок при выполнении запроса.
        
        Логирует информацию об ошибке.
        """
        # Извлекаем информацию об ошибке
        error = context.original_exception
        statement = context.statement
        parameters = context.parameters
        
        # Очищаем параметры от чувствительных данных
        if not self.log_sensitive_data:
            parameters = sanitize_payload(parameters)
        
        # Подготавливаем контекст для логирования
        log_context = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "statement_preview": self._get_statement_preview(statement),
            "parameters": truncate_payload(parameters),
        }
        
        # Логируем ошибку
        self.logger.error(f"Ошибка выполнения SQL: {log_context['error_message']}", extra=log_context)
    
    def _get_operation_type(self, statement: str) -> str:
        """
        Определяет тип операции по тексту SQL-запроса.
        
        Args:
            statement: Текст SQL-запроса
            
        Returns:
            Тип операции (SELECT, INSERT, UPDATE, DELETE, и т.д.)
        """
        if not statement:
            return "UNKNOWN"
        
        statement = statement.strip().upper()
        
        if statement.startswith("SELECT"):
            return "SELECT"
        elif statement.startswith("INSERT"):
            return "INSERT"
        elif statement.startswith("UPDATE"):
            return "UPDATE"
        elif statement.startswith("DELETE"):
            return "DELETE"
        elif statement.startswith("CREATE"):
            return "CREATE"
        elif statement.startswith("ALTER"):
            return "ALTER"
        elif statement.startswith("DROP"):
            return "DROP"
        elif statement.startswith("TRUNCATE"):
            return "TRUNCATE"
        elif statement.startswith("BEGIN"):
            return "BEGIN"
        elif statement.startswith("COMMIT"):
            return "COMMIT"
        elif statement.startswith("ROLLBACK"):
            return "ROLLBACK"
        else:
            # Извлекаем первое слово для других команд
            match = re.match(r'^\s*(\w+)', statement)
            if match:
                return match.group(1)
            return "UNKNOWN"
    
    def _get_statement_preview(self, statement: str, max_length: int = 200) -> str:
        """
        Формирует сокращенную версию запроса для логирования.
        
        Args:
            statement: Текст SQL-запроса
            max_length: Максимальная длина сокращенной версии
            
        Returns:
            Сокращенная версия запроса
        """
        if not statement:
            return ""
        
        # Удаляем лишние пробелы
        statement = re.sub(r'\s+', ' ', statement.strip())
        
        # Сокращаем, если слишком длинный
        if len(statement) > max_length:
            return statement[:max_length] + "..."
        
        return statement


def log_db_operation(
    operation_name: Optional[str] = None,
    log_args: bool = True,
    log_result: bool = True,
    log_exceptions: bool = True
) -> Callable[[F], F]:
    """
    Декоратор для логирования операций репозитория или сервиса с базой данных.
    
    Args:
        operation_name: Название операции (по умолчанию используется имя функции)
        log_args: Логировать ли аргументы функции
        log_result: Логировать ли результат функции
        log_exceptions: Логировать ли исключения
        
    Returns:
        Декорированная функция
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Получаем информацию о функции для логирования
            func_name = operation_name or func.__qualname__
            module_name = func.__module__
            
            # Создаем логгер
            logger = get_logger(f"{module_name}.db_operations")
            
            # Извлекаем информацию о классе, если функция - метод класса
            class_name = None
            if args and hasattr(args[0], "__class__"):
                class_name = args[0].__class__.__name__
                
            # Формируем название операции
            op_name = f"{class_name}.{func_name}" if class_name else func_name
            
            # Логируем начало операции
            start_time = time.time()
            
            log_context = {}
            
            # Логируем аргументы, если нужно
            if log_args:
                # Получаем имена параметров из сигнатуры функции
                sig = inspect.signature(func)
                param_names = list(sig.parameters.keys())
                
                # Создаем словарь аргументов
                func_args = {}
                
                # Добавляем позиционные аргументы
                for i, arg in enumerate(args):
                    # Пропускаем self или cls
                    if i == 0 and class_name:
                        continue
                    
                    arg_name = param_names[i] if i < len(param_names) else f"arg{i}"
                    func_args[arg_name] = arg
                
                # Добавляем именованные аргументы
                func_args.update(kwargs)
                
                # Очищаем аргументы от чувствительной информации
                clean_args = sanitize_payload(func_args)
                
                # Добавляем в контекст
                log_context["args"] = truncate_payload(clean_args)
            
            logger.debug(f"DB Operation {op_name}: starting", extra=log_context)
            
            try:
                # Выполняем операцию
                result = await func(*args, **kwargs)
                
                # Логируем результат
                duration = time.time() - start_time
                
                # Создаем контекст для логирования
                result_context = {
                    "duration_ms": round(duration * 1000, 2),
                }
                
                # Добавляем результат, если нужно
                if log_result and result is not None:
                    # Очищаем результат от чувствительной информации
                    clean_result = sanitize_payload(result)
                    result_context["result"] = truncate_payload(clean_result)
                    
                    # Добавляем количество элементов, если результат - коллекция
                    if isinstance(result, (list, tuple, set)):
                        result_context["count"] = len(result)
                
                logger.debug(
                    f"DB Operation {op_name}: completed in {result_context['duration_ms']} ms",
                    extra=result_context
                )
                
                return result
            
            except Exception as e:
                # Логируем исключение
                if log_exceptions:
                    duration = time.time() - start_time
                    
                    # Создаем контекст для логирования
                    error_context = {
                        "duration_ms": round(duration * 1000, 2),
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                    }
                    
                    logger.error(
                        f"DB Operation {op_name}: failed with {error_context['error_type']}",
                        extra=error_context,
                        exc_info=True
                    )
                
                # Пробрасываем исключение дальше
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Получаем информацию о функции для логирования
            func_name = operation_name or func.__qualname__
            module_name = func.__module__
            
            # Создаем логгер
            logger = get_logger(f"{module_name}.db_operations")
            
            # Извлекаем информацию о классе, если функция - метод класса
            class_name = None
            if args and hasattr(args[0], "__class__"):
                class_name = args[0].__class__.__name__
                
            # Формируем название операции
            op_name = f"{class_name}.{func_name}" if class_name else func_name
            
            # Логируем начало операции
            start_time = time.time()
            
            log_context = {}
            
            # Логируем аргументы, если нужно
            if log_args:
                # Получаем имена параметров из сигнатуры функции
                sig = inspect.signature(func)
                param_names = list(sig.parameters.keys())
                
                # Создаем словарь аргументов
                func_args = {}
                
                # Добавляем позиционные аргументы
                for i, arg in enumerate(args):
                    # Пропускаем self или cls
                    if i == 0 and class_name:
                        continue
                    
                    arg_name = param_names[i] if i < len(param_names) else f"arg{i}"
                    func_args[arg_name] = arg
                
                # Добавляем именованные аргументы
                func_args.update(kwargs)
                
                # Очищаем аргументы от чувствительной информации
                clean_args = sanitize_payload(func_args)
                
                # Добавляем в контекст
                log_context["args"] = truncate_payload(clean_args)
            
            logger.debug(f"DB Operation {op_name}: starting", extra=log_context)
            
            try:
                # Выполняем операцию
                result = func(*args, **kwargs)
                
                # Логируем результат
                duration = time.time() - start_time
                
                # Создаем контекст для логирования
                result_context = {
                    "duration_ms": round(duration * 1000, 2),
                }
                
                # Добавляем результат, если нужно
                if log_result and result is not None:
                    # Очищаем результат от чувствительной информации
                    clean_result = sanitize_payload(result)
                    result_context["result"] = truncate_payload(clean_result)
                    
                    # Добавляем количество элементов, если результат - коллекция
                    if isinstance(result, (list, tuple, set)):
                        result_context["count"] = len(result)
                
                logger.debug(
                    f"DB Operation {op_name}: completed in {result_context['duration_ms']} ms",
                    extra=result_context
                )
                
                return result
            
            except Exception as e:
                # Логируем исключение
                if log_exceptions:
                    duration = time.time() - start_time
                    
                    # Создаем контекст для логирования
                    error_context = {
                        "duration_ms": round(duration * 1000, 2),
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                    }
                    
                    logger.error(
                        f"DB Operation {op_name}: failed with {error_context['error_type']}",
                        extra=error_context,
                        exc_info=True
                    )
                
                # Пробрасываем исключение дальше
                raise
        
        # Выбираем подходящий враппер в зависимости от типа функции
        if inspect.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        return cast(F, sync_wrapper)
    
    return decorator


def setup_db_logging(
    engine: Union[Engine, AsyncEngine],
    slow_query_threshold: float = 1.0,
    log_level: str = "DEBUG"
) -> DatabaseLoggerMiddleware:
    """
    Настраивает и возвращает middleware для логирования операций с базой данных.
    
    Args:
        engine: SQLAlchemy Engine или AsyncEngine
        slow_query_threshold: Порог времени выполнения для медленных запросов (в секундах)
        log_level: Уровень логирования
        
    Returns:
        Настроенный middleware
    """
    return DatabaseLoggerMiddleware(
        engine=engine,
        slow_query_threshold=slow_query_threshold,
        log_sensitive_data=False,
        log_level=log_level
    )