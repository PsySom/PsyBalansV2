"""
Middleware для логирования операций с MongoDB.
"""
import time
import functools
import inspect
from typing import Any, Callable, Dict, List, Optional, Set, Type, TypeVar, Union, cast

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo import MongoClient
from pymongo.monitoring import CommandListener, CommandStartedEvent, CommandSucceededEvent, CommandFailedEvent

from app.core.logging import get_logger
from app.core.middleware.utils import sanitize_payload, truncate_payload

# Типы для декораторов
F = TypeVar('F', bound=Callable[..., Any])
T = TypeVar('T')


class MongoDBCommandLogger(CommandListener):
    """
    Слушатель команд MongoDB для логирования операций.
    """
    
    def __init__(
        self,
        slow_query_threshold: float = 1.0,
        log_sensitive_data: bool = False,
        log_level: str = "DEBUG"
    ):
        """
        Инициализирует слушателя команд MongoDB.
        
        Args:
            slow_query_threshold: Порог времени выполнения для медленных запросов (в секундах)
            log_sensitive_data: Логировать ли чувствительные данные (не рекомендуется)
            log_level: Уровень логирования (DEBUG, INFO, WARNING)
        """
        self.slow_query_threshold = slow_query_threshold
        self.log_sensitive_data = log_sensitive_data
        self.log_level = log_level.upper()
        
        self.logger = get_logger("app.db.mongodb")
    
    def started(self, event: CommandStartedEvent) -> None:
        """
        Вызывается при начале выполнения команды MongoDB.
        
        Args:
            event: Событие начала команды
        """
        # Если уровень логирования не DEBUG, не логируем начало команды
        if self.log_level != "DEBUG":
            return
        
        # Получаем информацию о команде
        command_name = event.command_name
        database_name = event.database_name
        
        # Очищаем команду от чувствительных данных, если нужно
        command = event.command
        if not self.log_sensitive_data:
            command = sanitize_payload(command)
        
        # Логируем начало выполнения команды
        log_context = {
            "request_id": event.request_id,
            "connection_id": event.connection_id,
            "operation_id": event.operation_id,
            "database": database_name,
            "command": truncate_payload(command),
        }
        
        self.logger.debug(f"MongoDB command started: {command_name}", extra=log_context)
    
    def succeeded(self, event: CommandSucceededEvent) -> None:
        """
        Вызывается при успешном выполнении команды MongoDB.
        
        Args:
            event: Событие успеха команды
        """
        # Получаем информацию о команде
        command_name = event.command_name
        database_name = event.database_name
        duration_ms = event.duration_micros / 1000  # в миллисекундах
        
        # Очищаем ответ от чувствительных данных, если нужно
        reply = event.reply
        if not self.log_sensitive_data:
            reply = sanitize_payload(reply)
        
        # Подготавливаем контекст для логирования
        log_context = {
            "request_id": event.request_id,
            "connection_id": event.connection_id,
            "operation_id": event.operation_id,
            "database": database_name,
            "duration_ms": round(duration_ms, 2),
        }
        
        # Добавляем ответ в контекст, если это не слишком большой объект
        if self.log_level == "DEBUG":
            log_context["reply"] = truncate_payload(reply)
        
        # Определяем, медленный ли запрос
        is_slow = duration_ms / 1000 >= self.slow_query_threshold
        
        # Логируем информацию о запросе
        log_message = f"MongoDB command {command_name} completed in {log_context['duration_ms']} ms"
        
        if is_slow:
            self.logger.warning(f"SLOW QUERY: {log_message}", extra=log_context)
        elif self.log_level == "DEBUG":
            self.logger.debug(log_message, extra=log_context)
        elif self.log_level == "INFO":
            self.logger.info(log_message, extra=log_context)
    
    def failed(self, event: CommandFailedEvent) -> None:
        """
        Вызывается при неудачном выполнении команды MongoDB.
        
        Args:
            event: Событие неудачи команды
        """
        # Получаем информацию о команде
        command_name = event.command_name
        database_name = event.database_name
        duration_ms = event.duration_micros / 1000  # в миллисекундах
        
        # Подготавливаем контекст для логирования
        log_context = {
            "request_id": event.request_id,
            "connection_id": event.connection_id,
            "operation_id": event.operation_id,
            "database": database_name,
            "duration_ms": round(duration_ms, 2),
            "error_type": type(event.failure).__name__ if event.failure else "Unknown",
            "error_message": str(event.failure),
        }
        
        # Логируем ошибку
        self.logger.error(
            f"MongoDB command {command_name} failed in {log_context['duration_ms']} ms: {log_context['error_message']}",
            extra=log_context
        )


class MongoDBLoggerMiddleware:
    """
    Middleware для логирования операций с MongoDB.
    
    Отслеживает выполнение команд MongoDB, измеряет время выполнения и
    логирует детали операций в структурированном формате.
    """
    
    def __init__(
        self,
        client: Union[MongoClient, AsyncIOMotorClient],
        slow_query_threshold: float = 1.0,
        log_sensitive_data: bool = False,
        log_level: str = "DEBUG"
    ):
        """
        Инициализация middleware для логирования операций с MongoDB.
        
        Args:
            client: Клиент MongoDB или Motor
            slow_query_threshold: Порог времени выполнения для медленных запросов (в секундах)
            log_sensitive_data: Логировать ли чувствительные данные (не рекомендуется)
            log_level: Уровень логирования (DEBUG, INFO, WARNING)
        """
        self.client = client
        self.slow_query_threshold = slow_query_threshold
        self.log_sensitive_data = log_sensitive_data
        self.log_level = log_level.upper()
        
        self.logger = get_logger("app.db.mongodb")
        
        # Создаем слушателя команд
        self.command_logger = MongoDBCommandLogger(
            slow_query_threshold=slow_query_threshold,
            log_sensitive_data=log_sensitive_data,
            log_level=log_level
        )
        
        # Добавляем слушателя к клиенту MongoDB
        self._setup_monitoring()
    
    def _setup_monitoring(self) -> None:
        """
        Настраивает мониторинг команд MongoDB.
        """
        # Регистрируем слушателя команд для глобального мониторинга
        # В новых версиях motor/pymongo нужно использовать другой подход
        # для доступа к базовому клиенту
        try:
            from pymongo.monitoring import register_command_listener
            register_command_listener(self.command_logger)
            self.logger.info("MongoDB command listener registered successfully")
        except Exception as e:
            self.logger.warning(f"Failed to register MongoDB command listener: {e}")


def log_mongodb_operation(
    operation_name: Optional[str] = None,
    log_args: bool = True,
    log_result: bool = True,
    log_exceptions: bool = True
) -> Callable[[F], F]:
    """
    Декоратор для логирования операций с MongoDB.
    
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
            logger = get_logger(f"{module_name}.mongodb_operations")
            
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
            
            # Пытаемся определить коллекцию или базу данных
            collection = None
            database = None
            
            if args and isinstance(args[0], AsyncIOMotorCollection):
                collection = args[0].name
                database = args[0].database.name
            elif args and isinstance(args[0], AsyncIOMotorDatabase):
                database = args[0].name
            
            if collection:
                log_context["collection"] = collection
            if database:
                log_context["database"] = database
            
            logger.debug(f"MongoDB operation {op_name}: starting", extra=log_context)
            
            try:
                # Выполняем операцию
                result = await func(*args, **kwargs)
                
                # Логируем результат
                duration = time.time() - start_time
                
                # Создаем контекст для логирования
                result_context = {
                    "duration_ms": round(duration * 1000, 2),
                }
                
                if collection:
                    result_context["collection"] = collection
                if database:
                    result_context["database"] = database
                
                # Добавляем результат, если нужно
                if log_result and result is not None:
                    # Очищаем результат от чувствительной информации
                    clean_result = sanitize_payload(result)
                    result_context["result"] = truncate_payload(clean_result)
                    
                    # Добавляем количество элементов, если результат - коллекция
                    if isinstance(result, (list, tuple, set)):
                        result_context["count"] = len(result)
                
                logger.debug(
                    f"MongoDB operation {op_name}: completed in {result_context['duration_ms']} ms",
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
                    
                    if collection:
                        error_context["collection"] = collection
                    if database:
                        error_context["database"] = database
                    
                    logger.error(
                        f"MongoDB operation {op_name}: failed with {error_context['error_type']}",
                        extra=error_context,
                        exc_info=True
                    )
                
                # Пробрасываем исключение дальше
                raise
        
        # Для асинхронных функций используем async_wrapper
        if inspect.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        
        # Для синхронных функций можно создать аналогичный sync_wrapper
        # Но поскольку Motor - асинхронный клиент, все функции должны быть асинхронными
        return cast(F, func)
    
    return decorator


def setup_mongodb_logging(
    client: Union[MongoClient, AsyncIOMotorClient],
    slow_query_threshold: float = 1.0,
    log_level: str = "DEBUG"
) -> MongoDBLoggerMiddleware:
    """
    Настраивает и возвращает middleware для логирования операций с MongoDB.
    
    Args:
        client: Клиент MongoDB или Motor
        slow_query_threshold: Порог времени выполнения для медленных запросов (в секундах)
        log_level: Уровень логирования
        
    Returns:
        Настроенный middleware
    """
    return MongoDBLoggerMiddleware(
        client=client,
        slow_query_threshold=slow_query_threshold,
        log_sensitive_data=False,
        log_level=log_level
    )