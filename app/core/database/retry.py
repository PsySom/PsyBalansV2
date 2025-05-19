"""
Модуль, содержащий механизм повторных попыток для обработки временных ошибок
при работе с базами данных.
"""
import asyncio
import functools
import logging
import random
import time
from typing import Any, Callable, ClassVar, Dict, List, Optional, Type, TypeVar, Union, cast

from app.core.exceptions.database import ConnectionError, DatabaseError, QueryError, TransactionError


# Тип для асинхронной функции
F = TypeVar('F', bound=Callable[..., Any])

# Логгер для механизма повторных попыток
logger = logging.getLogger("app.core.database.retry")


class RetryConfig:
    """
    Класс для настройки параметров повторных попыток.

    Attributes:
        max_attempts: Максимальное количество попыток (по умолчанию 3)
        base_delay: Базовая задержка в секундах перед повторной попыткой (по умолчанию 0.1 сек)
        max_delay: Максимальная задержка в секундах (по умолчанию 10 сек)
        jitter: Случайный фактор для добавления "шума" к задержке (по умолчанию 0.1)
        retry_exceptions: Список типов исключений, которые будут повторяться
        timeout: Общий таймаут для всех попыток (None = без таймаута)
    """
    # Исключения по умолчанию, которые будут повторяться
    DEFAULT_RETRY_EXCEPTIONS: ClassVar[List[Type[Exception]]] = [
        ConnectionError,
        QueryError,
        TransactionError,
        # Могут добавляться специфичные для драйверов исключения
        asyncio.TimeoutError,
    ]

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 0.1,
        max_delay: float = 10.0,
        jitter: float = 0.1,
        retry_exceptions: Optional[List[Type[Exception]]] = None,
        timeout: Optional[float] = None,
    ):
        """
        Инициализирует конфигурацию повторных попыток.

        Args:
            max_attempts: Максимальное количество попыток (включая начальную)
            base_delay: Базовая задержка в секундах
            max_delay: Максимальная задержка в секундах
            jitter: Случайный фактор (0.0 - без случайности, 1.0 - полностью случайная задержка)
            retry_exceptions: Список типов исключений для повторных попыток
            timeout: Общий таймаут в секундах для всех попыток
        """
        if max_attempts < 1:
            raise ValueError("max_attempts должно быть больше 0")
        if base_delay <= 0:
            raise ValueError("base_delay должно быть положительным числом")
        if max_delay < base_delay:
            raise ValueError("max_delay должно быть больше или равно base_delay")
        if not (0 <= jitter <= 1):
            raise ValueError("jitter должен быть в диапазоне от 0 до 1")

        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
        self.retry_exceptions = retry_exceptions or self.DEFAULT_RETRY_EXCEPTIONS.copy()
        self.timeout = timeout

    def calculate_delay(self, attempt: int) -> float:
        """
        Вычисляет задержку перед следующей попыткой с использованием
        алгоритма экспоненциального отступа (exponential backoff).

        Args:
            attempt: Номер текущей попытки (начиная с 1)

        Returns:
            float: Время задержки в секундах
        """
        # Экспоненциальный отступ: delay = base_delay * 2^(attempt-1)
        delay = self.base_delay * (2 ** (attempt - 1))
        
        # Применяем максимальное ограничение
        delay = min(delay, self.max_delay)
        
        # Добавляем случайный "шум" (jitter)
        if self.jitter > 0:
            jitter_factor = random.uniform(-self.jitter, self.jitter)
            delay = delay * (1 + jitter_factor)
        
        # Убеждаемся, что задержка не отрицательная
        return max(0, delay)

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """
        Определяет, следует ли повторить операцию после данного исключения.

        Args:
            exception: Возникшее исключение
            attempt: Номер текущей попытки

        Returns:
            bool: True, если следует повторить, иначе False
        """
        # Проверяем, что не превышено максимальное количество попыток
        if attempt >= self.max_attempts:
            return False
        
        # Проверяем, входит ли исключение в список повторяемых
        for exception_type in self.retry_exceptions:
            if isinstance(exception, exception_type):
                return True
        
        return False

    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует конфигурацию в словарь для логирования или сериализации.

        Returns:
            Dict[str, Any]: Словарь с параметрами конфигурации
        """
        return {
            "max_attempts": self.max_attempts,
            "base_delay": self.base_delay,
            "max_delay": self.max_delay,
            "jitter": self.jitter,
            "retry_exceptions": [exc.__name__ for exc in self.retry_exceptions],
            "timeout": self.timeout
        }


def with_retry(
    func: Optional[F] = None,
    *,
    retry_config: Optional[RetryConfig] = None,
    **config_kwargs: Any,
) -> Union[F, Callable[[F], F]]:
    """
    Декоратор для выполнения асинхронных функций с механизмом повторных попыток
    при возникновении временных ошибок.

    Использование:
        @with_retry
        async def my_function():
            ...

        @with_retry(max_attempts=5, base_delay=0.2)
        async def my_other_function():
            ...

    Args:
        func: Декорируемая функция
        retry_config: Экземпляр RetryConfig с настройками повторных попыток
        **config_kwargs: Параметры для создания RetryConfig, если он не передан

    Returns:
        Callable: Декорированная функция
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Определяем конфигурацию повторных попыток
            config = retry_config or RetryConfig(**config_kwargs)
            
            # Информация о функции для логирования
            func_name = func.__qualname__
            module_name = func.__module__
            func_info = f"{module_name}.{func_name}"
            
            # Счетчик попыток
            attempt = 1
            start_time = time.time()
            
            # Если установлен общий таймаут, создаем таймер
            overall_timeout = None
            if config.timeout:
                overall_timeout = start_time + config.timeout
            
            while True:
                try:
                    # Если установлен таймаут и он истек, вызываем исключение
                    if overall_timeout and time.time() >= overall_timeout:
                        raise asyncio.TimeoutError(
                            f"Общий таймаут {config.timeout}с истек для {func_info}"
                        )
                    
                    # Выполняем функцию
                    start_attempt = time.time()
                    result = await func(*args, **kwargs)
                    duration = time.time() - start_attempt
                    
                    # Если это не первая попытка, логируем успешное выполнение
                    if attempt > 1:
                        logger.info(
                            f"Операция {func_info} успешно выполнена после {attempt} попыток за {duration:.3f}с"
                        )
                    
                    return result
                
                except Exception as e:
                    # Время, затраченное на попытку
                    duration = time.time() - start_attempt
                    
                    # Проверяем, следует ли повторить операцию
                    if not config.should_retry(e, attempt):
                        # Если повторная попытка не требуется, пробрасываем исключение выше
                        if attempt > 1:
                            logger.warning(
                                f"Операция {func_info} не удалась после {attempt} попыток. "
                                f"Последнее исключение: {type(e).__name__}: {str(e)}"
                            )
                        
                        # Если это исключение базы данных, дополняем его информацией о попытках
                        if isinstance(e, DatabaseError):
                            if not hasattr(e, 'retry_attempts'):
                                e.retry_attempts = attempt  # type: ignore
                            if not hasattr(e, 'retry_duration'):
                                e.retry_duration = time.time() - start_time  # type: ignore
                        
                        raise
                    
                    # Вычисляем задержку перед следующей попыткой
                    delay = config.calculate_delay(attempt)
                    
                    # Логируем информацию о повторной попытке
                    logger.warning(
                        f"Попытка {attempt} операции {func_info} не удалась за {duration:.3f}с: "
                        f"{type(e).__name__}: {str(e)}. Повторная попытка через {delay:.3f}с..."
                    )
                    
                    # Увеличиваем счетчик попыток
                    attempt += 1
                    
                    # Выполняем задержку перед следующей попыткой
                    await asyncio.sleep(delay)
            
        return cast(F, wrapper)
    
    # Поддержка использования декоратора как с параметрами, так и без них
    if func is None:
        return decorator
    return decorator(func)


# Глобальная конфигурация повторных попыток по умолчанию
default_retry_config = RetryConfig()


def configure_default_retry(
    max_attempts: Optional[int] = None,
    base_delay: Optional[float] = None,
    max_delay: Optional[float] = None,
    jitter: Optional[float] = None,
    retry_exceptions: Optional[List[Type[Exception]]] = None,
    timeout: Optional[float] = None,
) -> None:
    """
    Настраивает глобальную конфигурацию повторных попыток по умолчанию.

    Args:
        max_attempts: Максимальное количество попыток
        base_delay: Базовая задержка в секундах
        max_delay: Максимальная задержка в секундах
        jitter: Случайный фактор для задержки
        retry_exceptions: Список исключений для повторных попыток
        timeout: Общий таймаут в секундах
    """
    global default_retry_config
    
    # Создаем новый словарь конфигурации, обновляя только переданные параметры
    config_dict = default_retry_config.to_dict()
    
    # Обновляем только те параметры, которые были явно указаны
    if max_attempts is not None:
        config_dict["max_attempts"] = max_attempts
    if base_delay is not None:
        config_dict["base_delay"] = base_delay
    if max_delay is not None:
        config_dict["max_delay"] = max_delay
    if jitter is not None:
        config_dict["jitter"] = jitter
    if timeout is not None:
        config_dict["timeout"] = timeout
    
    # Для исключений обрабатываем отдельно, чтобы сохранить список объектов классов
    if retry_exceptions is not None:
        for exc_type in retry_exceptions:
            if not issubclass(exc_type, Exception):
                raise TypeError(f"{exc_type.__name__} не является подклассом Exception")
    
    # Создаем обновленную конфигурацию
    new_config = RetryConfig(
        max_attempts=config_dict["max_attempts"],
        base_delay=config_dict["base_delay"],
        max_delay=config_dict["max_delay"],
        jitter=config_dict["jitter"],
        timeout=config_dict["timeout"],
        # Для типа исключений используем переданный список или текущий
        retry_exceptions=retry_exceptions or default_retry_config.retry_exceptions
    )
    
    # Обновляем глобальную конфигурацию
    default_retry_config = new_config
    
    logger.info(f"Обновлена глобальная конфигурация повторных попыток: {new_config.to_dict()}")


__all__ = [
    "RetryConfig",
    "with_retry",
    "default_retry_config",
    "configure_default_retry"
]