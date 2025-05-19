"""
Модуль, содержащий иерархию исключений для работы с базами данных.

Эти исключения используются для унифицированной обработки различных типов
ошибок, возникающих при работе с базами данных (PostgreSQL и MongoDB).
"""
from typing import Any, Dict, Optional, List, Union
import traceback


class DatabaseError(Exception):
    """
    Базовый класс для всех исключений, связанных с базами данных.
    
    Атрибуты:
        message (str): Сообщение об ошибке
        code (Optional[str]): Код ошибки
        details (Optional[Dict[str, Any]]): Дополнительные детали об ошибке
        source (Optional[str]): Источник ошибки (например, "postgresql", "mongodb")
        cause (Optional[Exception]): Исходное исключение, вызвавшее эту ошибку
    """
    
    def __init__(
        self, 
        message: str, 
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
        cause: Optional[Exception] = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        self.source = source
        self.cause = cause
        
        # Формируем полное сообщение об ошибке
        full_message = self.format_message()
        super().__init__(full_message)
    
    def format_message(self) -> str:
        """
        Форматирует сообщение об ошибке, добавляя дополнительную информацию.
        
        Returns:
            str: Отформатированное сообщение об ошибке
        """
        parts = [self.message]
        
        if self.code:
            parts.append(f"[Код: {self.code}]")
        
        if self.source:
            parts.append(f"[Источник: {self.source}]")
        
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            parts.append(f"[Детали: {details_str}]")
        
        if self.cause:
            cause_info = f"{type(self.cause).__name__}: {str(self.cause)}"
            parts.append(f"[Первопричина: {cause_info}]")
        
        return " ".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует исключение в словарь для сериализации.
        
        Returns:
            Dict[str, Any]: Словарь с информацией об ошибке
        """
        error_dict = {
            "error_type": self.__class__.__name__,
            "message": self.message,
        }
        
        if self.code:
            error_dict["code"] = self.code
        
        if self.source:
            error_dict["source"] = self.source
        
        if self.details:
            error_dict["details"] = self.details
        
        if self.cause:
            error_dict["cause"] = {
                "type": type(self.cause).__name__,
                "message": str(self.cause)
            }
        
        return error_dict
    
    @classmethod
    def from_exception(cls, exception: Exception, message: Optional[str] = None, **kwargs) -> 'DatabaseError':
        """
        Создает экземпляр DatabaseError из существующего исключения.
        
        Args:
            exception: Исходное исключение
            message: Пользовательское сообщение (если не указано, используется str(exception))
            **kwargs: Дополнительные параметры для конструктора DatabaseError
        
        Returns:
            DatabaseError: Новый экземпляр DatabaseError
        """
        return cls(
            message=message or str(exception),
            cause=exception,
            **kwargs
        )


class ConnectionError(DatabaseError):
    """
    Исключение, возникающее при проблемах с соединением к базе данных.
    
    Атрибуты:
        connection_params (Optional[Dict[str, Any]]): Параметры соединения (без учетных данных)
        retry_count (Optional[int]): Количество попыток соединения
        max_retries (Optional[int]): Максимальное количество попыток
    """
    
    def __init__(
        self, 
        message: str, 
        connection_params: Optional[Dict[str, Any]] = None,
        retry_count: Optional[int] = None,
        max_retries: Optional[int] = None,
        **kwargs
    ):
        self.connection_params = self._sanitize_connection_params(connection_params or {})
        self.retry_count = retry_count
        self.max_retries = max_retries
        
        # Добавляем информацию о соединении в детали
        details = kwargs.get('details', {})
        if self.connection_params:
            details['connection_params'] = self.connection_params
        
        if retry_count is not None:
            details['retry_count'] = retry_count
            
        if max_retries is not None:
            details['max_retries'] = max_retries
            
        kwargs['details'] = details
        super().__init__(message, **kwargs)
    
    def _sanitize_connection_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Удаляет конфиденциальную информацию из параметров соединения.
        
        Args:
            params: Исходные параметры соединения
            
        Returns:
            Dict[str, Any]: Очищенные параметры соединения
        """
        # Создаем копию, чтобы не изменять оригинал
        sanitized = params.copy()
        
        # Удаляем конфиденциальные данные
        sensitive_keys = ['password', 'pwd', 'secret', 'key', 'token', 'auth']
        for key in list(sanitized.keys()):
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = '***'
        
        return sanitized


class QueryError(DatabaseError):
    """
    Исключение, возникающее при ошибках в запросах к базе данных.
    
    Атрибуты:
        query (Optional[str]): Текст запроса (для SQL) или операция (для NoSQL)
        params (Optional[Dict[str, Any]]): Параметры запроса
        execution_time (Optional[float]): Время выполнения запроса в миллисекундах
    """
    
    def __init__(
        self, 
        message: str, 
        query: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        execution_time: Optional[float] = None,
        **kwargs
    ):
        self.query = query
        self.params = params
        self.execution_time = execution_time
        
        # Добавляем информацию о запросе в детали
        details = kwargs.get('details', {})
        if query:
            details['query'] = query
        
        if params:
            details['params'] = params
            
        if execution_time is not None:
            details['execution_time'] = f"{execution_time:.2f}ms"
            
        kwargs['details'] = details
        super().__init__(message, **kwargs)


class ValidationError(DatabaseError):
    """
    Исключение, возникающее при ошибках валидации данных.
    
    Атрибуты:
        field_errors (Dict[str, List[str]]): Словарь ошибок валидации по полям
        model (Optional[str]): Имя модели или коллекции
        value (Optional[Any]): Значение, которое не прошло валидацию
    """
    
    def __init__(
        self, 
        message: str, 
        field_errors: Optional[Dict[str, List[str]]] = None,
        model: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs
    ):
        self.field_errors = field_errors or {}
        self.model = model
        self.value = value
        
        # Добавляем информацию о валидации в детали
        details = kwargs.get('details', {})
        if field_errors:
            details['field_errors'] = field_errors
        
        if model:
            details['model'] = model
            
        kwargs['details'] = details
        super().__init__(message, **kwargs)
    
    def format_message(self) -> str:
        """
        Форматирует сообщение об ошибке, добавляя информацию об ошибках валидации.
        
        Returns:
            str: Отформатированное сообщение об ошибке
        """
        base_message = super().format_message()
        
        if not self.field_errors:
            return base_message
        
        # Добавляем информацию об ошибках валидации полей
        field_errors_formatted = []
        for field, errors in self.field_errors.items():
            error_str = ", ".join(errors)
            field_errors_formatted.append(f"{field}: {error_str}")
        
        field_errors_str = "; ".join(field_errors_formatted)
        return f"{base_message} Ошибки полей: {field_errors_str}"


class IntegrityError(DatabaseError):
    """
    Исключение, возникающее при нарушении целостности данных.
    
    Атрибуты:
        constraint_name (Optional[str]): Имя нарушенного ограничения
        table_name (Optional[str]): Имя таблицы или коллекции
        columns (Optional[List[str]]): Список затронутых столбцов
    """
    
    def __init__(
        self, 
        message: str, 
        constraint_name: Optional[str] = None,
        table_name: Optional[str] = None,
        columns: Optional[List[str]] = None,
        **kwargs
    ):
        self.constraint_name = constraint_name
        self.table_name = table_name
        self.columns = columns or []
        
        # Добавляем информацию о целостности данных в детали
        details = kwargs.get('details', {})
        if constraint_name:
            details['constraint_name'] = constraint_name
        
        if table_name:
            details['table_name'] = table_name
            
        if columns:
            details['columns'] = columns
            
        kwargs['details'] = details
        super().__init__(message, **kwargs)


class NotFoundError(DatabaseError):
    """
    Исключение, возникающее, когда ресурс не найден в базе данных.
    
    Атрибуты:
        resource_type (Optional[str]): Тип ресурса (например, "User", "Activity")
        resource_id (Optional[Union[str, int]]): Идентификатор ресурса
        query_params (Optional[Dict[str, Any]]): Параметры запроса
    """
    
    def __init__(
        self, 
        message: str, 
        resource_type: Optional[str] = None,
        resource_id: Optional[Union[str, int]] = None,
        query_params: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.query_params = query_params
        
        # Добавляем информацию о ресурсе в детали
        details = kwargs.get('details', {})
        if resource_type:
            details['resource_type'] = resource_type
        
        if resource_id:
            details['resource_id'] = str(resource_id)
            
        if query_params:
            details['query_params'] = query_params
            
        kwargs['details'] = details
        super().__init__(message, **kwargs)


class DuplicateError(DatabaseError):
    """
    Исключение, возникающее при попытке создать дубликат уникального ресурса.
    
    Атрибуты:
        resource_type (Optional[str]): Тип ресурса (например, "User", "Activity")
        unique_field (Optional[str]): Имя поля с уникальным ограничением
        duplicate_value (Optional[Any]): Дублирующееся значение
    """
    
    def __init__(
        self, 
        message: str, 
        resource_type: Optional[str] = None,
        unique_field: Optional[str] = None,
        duplicate_value: Optional[Any] = None,
        **kwargs
    ):
        self.resource_type = resource_type
        self.unique_field = unique_field
        self.duplicate_value = duplicate_value
        
        # Добавляем информацию о дубликате в детали
        details = kwargs.get('details', {})
        if resource_type:
            details['resource_type'] = resource_type
        
        if unique_field:
            details['unique_field'] = unique_field
            
        if duplicate_value is not None:
            details['duplicate_value'] = str(duplicate_value)
            
        kwargs['details'] = details
        super().__init__(message, **kwargs)


class TransactionError(DatabaseError):
    """
    Исключение, возникающее при ошибках в транзакциях.
    
    Атрибуты:
        transaction_id (Optional[str]): Идентификатор транзакции
        operation (Optional[str]): Операция, вызвавшая ошибку (commit, rollback, etc.)
        state (Optional[str]): Состояние транзакции на момент ошибки
    """
    
    def __init__(
        self, 
        message: str, 
        transaction_id: Optional[str] = None,
        operation: Optional[str] = None,
        state: Optional[str] = None,
        **kwargs
    ):
        self.transaction_id = transaction_id
        self.operation = operation
        self.state = state
        
        # Добавляем информацию о транзакции в детали
        details = kwargs.get('details', {})
        if transaction_id:
            details['transaction_id'] = transaction_id
        
        if operation:
            details['operation'] = operation
            
        if state:
            details['state'] = state
            
        kwargs['details'] = details
        super().__init__(message, **kwargs)
    
    @classmethod
    def from_transaction_exception(
        cls, 
        exception: Exception, 
        operation: str, 
        transaction_id: Optional[str] = None,
        **kwargs
    ) -> 'TransactionError':
        """
        Создает экземпляр TransactionError из исключения, возникшего в транзакции.
        
        Args:
            exception: Исходное исключение
            operation: Операция транзакции
            transaction_id: Идентификатор транзакции
            **kwargs: Дополнительные параметры
        
        Returns:
            TransactionError: Новый экземпляр TransactionError
        """
        return cls(
            message=f"Ошибка в транзакции при выполнении операции '{operation}': {str(exception)}",
            transaction_id=transaction_id,
            operation=operation,
            cause=exception,
            **kwargs
        )


# Экспортируем все классы исключений
__all__ = [
    "DatabaseError",
    "ConnectionError",
    "QueryError",
    "ValidationError",
    "IntegrityError",
    "NotFoundError",
    "DuplicateError",
    "TransactionError"
]