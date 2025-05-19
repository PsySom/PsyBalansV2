"""
Модуль, реализующий паттерн Circuit Breaker для предотвращения каскадных отказов
при работе с внешними сервисами или базами данных.
"""
import asyncio
import enum
import functools
import inspect
import time
import threading
import random
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set, Type, TypeVar, Union, cast

from app.core.logging import get_logger

# Типы для декораторов
F = TypeVar('F', bound=Callable[..., Any])
T = TypeVar('T')


class CircuitState(enum.Enum):
    """
    Состояния Circuit Breaker.
    
    - CLOSED: Нормальное состояние, запросы проходят
    - OPEN: Состояние сбоя, запросы блокируются
    - HALF_OPEN: Состояние восстановления, пропускается ограниченное количество запросов
    """
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerError(Exception):
    """
    Исключение, генерируемое при отклонении запроса Circuit Breaker.
    """
    def __init__(
        self, 
        message: str, 
        circuit_name: str, 
        state: CircuitState,
        last_error: Optional[Exception] = None
    ):
        """
        Инициализирует исключение CircuitBreakerError.
        
        Args:
            message: Сообщение об ошибке
            circuit_name: Имя Circuit Breaker
            state: Состояние Circuit Breaker
            last_error: Последнее исключение, вызвавшее открытие цепи
        """
        self.circuit_name = circuit_name
        self.state = state
        self.last_error = last_error
        super().__init__(message)


class CircuitBreaker:
    """
    Реализация паттерна Circuit Breaker для предотвращения каскадных отказов.
    
    Circuit Breaker отслеживает количество сбоев при вызове внешнего сервиса или
    базы данных и автоматически блокирует запросы, если количество сбоев превышает
    пороговое значение, предотвращая каскадные отказы и перегрузку системы.
    """
    
    # Словарь для хранения всех экземпляров CircuitBreaker по имени
    _instances: Dict[str, 'CircuitBreaker'] = {}
    _lock = threading.RLock()
    
    @classmethod
    def get_or_create(
        cls,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3,
        call_timeout: Optional[float] = None,
        excluded_exceptions: Optional[List[Type[Exception]]] = None
    ) -> 'CircuitBreaker':
        """
        Получает существующий или создает новый экземпляр CircuitBreaker.
        
        Args:
            name: Уникальное имя для Circuit Breaker
            failure_threshold: Количество ошибок для открытия цепи
            recovery_timeout: Время в секундах до перехода в полуоткрытое состояние
            half_open_max_calls: Максимальное количество вызовов в полуоткрытом состоянии
            call_timeout: Таймаут для вызовов в секундах
            excluded_exceptions: Исключения, которые не считаются ошибками
            
        Returns:
            Экземпляр CircuitBreaker
        """
        with cls._lock:
            if name not in cls._instances:
                cls._instances[name] = CircuitBreaker(
                    name=name,
                    failure_threshold=failure_threshold,
                    recovery_timeout=recovery_timeout,
                    half_open_max_calls=half_open_max_calls,
                    call_timeout=call_timeout,
                    excluded_exceptions=excluded_exceptions
                )
            return cls._instances[name]
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3,
        call_timeout: Optional[float] = None,
        excluded_exceptions: Optional[List[Type[Exception]]] = None
    ):
        """
        Инициализирует Circuit Breaker.
        
        Args:
            name: Уникальное имя для Circuit Breaker
            failure_threshold: Количество ошибок для открытия цепи
            recovery_timeout: Время в секундах до перехода в полуоткрытое состояние
            half_open_max_calls: Максимальное количество вызовов в полуоткрытом состоянии
            call_timeout: Таймаут для вызовов в секундах
            excluded_exceptions: Исключения, которые не считаются ошибками
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.call_timeout = call_timeout
        self.excluded_exceptions = excluded_exceptions or []
        
        # Состояние Circuit Breaker
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._last_failure_time: Optional[float] = None
        self._last_error: Optional[Exception] = None
        self._successful_calls = 0
        self._half_open_calls = 0
        
        # Для thread-safety
        self._lock = threading.RLock()
        
        # Логгер
        self.logger = get_logger(f"app.circuit_breaker.{name}")
    
    @property
    def state(self) -> CircuitState:
        """
        Возвращает текущее состояние Circuit Breaker.
        
        Returns:
            Состояние Circuit Breaker
        """
        # Проверяем переход из OPEN в HALF_OPEN по таймауту
        if self._state == CircuitState.OPEN and self._last_failure_time:
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._transition_to_half_open()
        
        return self._state
    
    @property
    def failures(self) -> int:
        """
        Возвращает текущее количество последовательных сбоев.
        
        Returns:
            Количество сбоев
        """
        return self._failures
    
    @property
    def last_failure_time(self) -> Optional[datetime]:
        """
        Возвращает время последнего сбоя.
        
        Returns:
            Время последнего сбоя или None
        """
        if self._last_failure_time:
            return datetime.fromtimestamp(self._last_failure_time)
        return None
    
    def _transition_to_open(self, error: Optional[Exception] = None) -> None:
        """
        Переводит Circuit Breaker в состояние OPEN.
        
        Args:
            error: Исключение, вызвавшее переход
        """
        with self._lock:
            if self._state != CircuitState.OPEN:
                self._state = CircuitState.OPEN
                self._last_failure_time = time.time()
                self._last_error = error
                
                self.logger.warning(
                    f"Circuit {self.name} changed state to OPEN after {self._failures} failures",
                    extra={
                        "circuit_name": self.name,
                        "new_state": self._state.value,
                        "failures": self._failures,
                        "last_error": str(error) if error else None,
                        "error_type": type(error).__name__ if error else None,
                        "recovery_timeout": self.recovery_timeout
                    }
                )
    
    def _transition_to_half_open(self) -> None:
        """
        Переводит Circuit Breaker в состояние HALF_OPEN.
        """
        with self._lock:
            if self._state != CircuitState.HALF_OPEN:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                
                self.logger.info(
                    f"Circuit {self.name} changed state to HALF_OPEN after {self.recovery_timeout}s timeout",
                    extra={
                        "circuit_name": self.name,
                        "new_state": self._state.value,
                        "recovery_timeout": self.recovery_timeout,
                        "half_open_max_calls": self.half_open_max_calls
                    }
                )
    
    def _transition_to_closed(self) -> None:
        """
        Переводит Circuit Breaker в состояние CLOSED.
        """
        with self._lock:
            if self._state != CircuitState.CLOSED:
                self._state = CircuitState.CLOSED
                self._failures = 0
                self._successful_calls = 0
                self._last_error = None
                
                self.logger.info(
                    f"Circuit {self.name} changed state to CLOSED after successful recovery",
                    extra={
                        "circuit_name": self.name,
                        "new_state": self._state.value
                    }
                )
    
    def _record_success(self) -> None:
        """
        Регистрирует успешный вызов.
        """
        with self._lock:
            current_state = self._state
            
            if current_state == CircuitState.CLOSED:
                # В закрытом состоянии сбрасываем счетчик ошибок
                self._failures = 0
                self._successful_calls += 1
            
            elif current_state == CircuitState.HALF_OPEN:
                # В полуоткрытом состоянии увеличиваем счетчик успешных вызовов
                self._successful_calls += 1
                self._half_open_calls += 1
                
                # Если достигнуто необходимое количество успешных вызовов,
                # переходим в закрытое состояние
                if self._successful_calls >= self.half_open_max_calls:
                    self._transition_to_closed()
    
    def _record_failure(self, error: Exception) -> None:
        """
        Регистрирует сбой вызова.
        
        Args:
            error: Исключение, вызвавшее сбой
        """
        # Проверяем, является ли исключение исключенным
        if any(isinstance(error, exc_type) for exc_type in self.excluded_exceptions):
            return
        
        with self._lock:
            current_state = self._state
            
            if current_state == CircuitState.CLOSED:
                # В закрытом состоянии увеличиваем счетчик ошибок
                self._failures += 1
                
                # Если превышен порог ошибок, переходим в открытое состояние
                if self._failures >= self.failure_threshold:
                    self._transition_to_open(error)
                else:
                    self.logger.debug(
                        f"Circuit {self.name} recorded failure ({self._failures}/{self.failure_threshold})",
                        extra={
                            "circuit_name": self.name,
                            "state": self._state.value,
                            "failures": self._failures,
                            "threshold": self.failure_threshold,
                            "error_type": type(error).__name__
                        }
                    )
            
            elif current_state == CircuitState.HALF_OPEN:
                # В полуоткрытом состоянии сразу переходим в открытое при ошибке
                self._half_open_calls += 1
                self._transition_to_open(error)
    
    def allow_request(self) -> bool:
        """
        Проверяет, разрешено ли выполнение запроса.
        
        Returns:
            True, если запрос разрешен, иначе False
        """
        current_state = self.state  # Это обновит состояние при необходимости
        
        if current_state == CircuitState.CLOSED:
            # В закрытом состоянии все запросы разрешены
            return True
        
        elif current_state == CircuitState.OPEN:
            # В открытом состоянии все запросы запрещены
            return False
        
        elif current_state == CircuitState.HALF_OPEN:
            # В полуоткрытом состоянии разрешается ограниченное количество запросов
            with self._lock:
                if self._half_open_calls < self.half_open_max_calls:
                    # Разрешаем запрос
                    return True
                else:
                    # Слишком много запросов в полуоткрытом состоянии
                    return False
        
        return False
    
    def __call__(self, func: F) -> F:
        """
        Декоратор для защиты функции с использованием Circuit Breaker.
        
        Args:
            func: Функция для защиты
            
        Returns:
            Декорированная функция
        """
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            if not self.allow_request():
                # Запрос не разрешен, генерируем исключение
                raise CircuitBreakerError(
                    f"Circuit {self.name} is {self.state.value}, request rejected",
                    self.name,
                    self.state,
                    self._last_error
                )
            
            try:
                # Если задан таймаут, используем его
                if self.call_timeout:
                    try:
                        # Выполняем функцию с таймаутом
                        result = await asyncio.wait_for(
                            func(*args, **kwargs),
                            timeout=self.call_timeout
                        )
                    except asyncio.TimeoutError:
                        # Таймаут считается ошибкой
                        error = asyncio.TimeoutError(
                            f"Call timed out after {self.call_timeout}s"
                        )
                        self._record_failure(error)
                        raise
                else:
                    # Выполняем функцию без таймаута
                    result = await func(*args, **kwargs)
                
                # Регистрируем успешное выполнение
                self._record_success()
                return result
                
            except Exception as e:
                # Регистрируем ошибку
                self._record_failure(e)
                
                # Пробрасываем исключение дальше
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            if not self.allow_request():
                # Запрос не разрешен, генерируем исключение
                raise CircuitBreakerError(
                    f"Circuit {self.name} is {self.state.value}, request rejected",
                    self.name,
                    self.state,
                    self._last_error
                )
            
            try:
                # Выполняем функцию
                result = func(*args, **kwargs)
                
                # Регистрируем успешное выполнение
                self._record_success()
                return result
                
            except Exception as e:
                # Регистрируем ошибку
                self._record_failure(e)
                
                # Пробрасываем исключение дальше
                raise
        
        # Выбираем подходящий враппер в зависимости от типа функции
        if inspect.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        return cast(F, sync_wrapper)


def circuit_breaker(
    name: Optional[str] = None,
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
    half_open_max_calls: int = 3,
    call_timeout: Optional[float] = None,
    excluded_exceptions: Optional[List[Type[Exception]]] = None
) -> Callable[[F], F]:
    """
    Декоратор для защиты функции с использованием Circuit Breaker.
    
    Args:
        name: Уникальное имя для Circuit Breaker (по умолчанию имя функции)
        failure_threshold: Количество ошибок для открытия цепи
        recovery_timeout: Время в секундах до перехода в полуоткрытое состояние
        half_open_max_calls: Максимальное количество вызовов в полуоткрытом состоянии
        call_timeout: Таймаут для вызовов в секундах
        excluded_exceptions: Исключения, которые не считаются ошибками
        
    Returns:
        Декоратор для функции
    """
    def decorator(func: F) -> F:
        # Если имя не указано, используем имя функции
        circuit_name = name or f"{func.__module__}.{func.__qualname__}"
        
        # Получаем или создаем Circuit Breaker
        cb = CircuitBreaker.get_or_create(
            name=circuit_name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            half_open_max_calls=half_open_max_calls,
            call_timeout=call_timeout,
            excluded_exceptions=excluded_exceptions
        )
        
        # Применяем Circuit Breaker как декоратор
        return cb(func)
    
    return decorator