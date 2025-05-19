"""
Утилиты для работы с middleware и безопасного логирования.
"""
import copy
import json
import re
from typing import Any, Dict, List, Optional, Pattern, Set, Union


class SensitiveDataFilter:
    """
    Фильтр для маскирования чувствительной информации в логах.
    """
    
    # Названия полей, которые могут содержать чувствительную информацию
    SENSITIVE_FIELDS: Set[str] = {
        # Аутентификация и безопасность
        'password', 'passwd', 'pass', 'secret', 'key', 'token', 'auth', 'credential',
        'api_key', 'apikey', 'access_token', 'refresh_token', 'jwt', 'private_key',
        'security_code', 'security_answer', 'pin', 'otp', 'mfa',
        
        # Персональные данные
        'ssn', 'social_security', 'tax_id', 'passport', 'driver_license', 'credit_card',
        'card_number', 'card_cvv', 'cvv', 'expiry', 'expiration',
        
        # Контактная информация
        'email', 'phone', 'mobile', 'address', 'zip', 'postal', 'city', 'country',
        
        # Финансы
        'account_number', 'routing_number', 'iban', 'bic', 'swift', 'bank_account',
        'balance', 'payment', 'salary', 'income', 'tax'
    }
    
    # Шаблоны для поиска чувствительной информации в строках
    SENSITIVE_PATTERNS: List[Pattern] = [
        # Кредитные карты (основные форматы)
        re.compile(r'\b(?:\d[ -]*?){13,16}\b'),
        # Электронная почта
        re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        # Токены и ключи API (обычно длинные хеши или base64)
        re.compile(r'eyJ[a-zA-Z0-9_=-]{5,}\.eyJ[a-zA-Z0-9_=-]{5,}'),  # JWT
        re.compile(r'\b[A-Za-z0-9+/]{40,}={0,2}\b'),  # Base64
        re.compile(r'\b[0-9a-f]{32,}\b'),  # MD5/SHA-подобные хеши
        # Пароли в URL
        re.compile(r'(https?://)([^:]+):([^@]+)@'),
    ]
    
    # Замена для маскировки чувствительных данных
    MASK: str = "***"
    
    @classmethod
    def filter_sensitive_data(cls, data: Any) -> Any:
        """
        Фильтрует чувствительные данные в различных типах объектов.
        
        Args:
            data: Данные для фильтрации
            
        Returns:
            Объект с замаскированными чувствительными данными
        """
        if data is None:
            return None
        
        # Для dict
        if isinstance(data, dict):
            return cls._filter_dict(data)
        
        # Для list, tuple, set
        if isinstance(data, (list, tuple, set)):
            return cls._filter_iterable(data)
        
        # Для строк
        if isinstance(data, str):
            return cls._filter_string(data)
        
        # Для простых типов данных
        if isinstance(data, (int, float, bool)):
            return data
        
        # Для всех остальных типов преобразуем в строку
        try:
            return str(data)
        except Exception:
            return "<unprintable object>"
    
    @classmethod
    def _filter_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Фильтрует чувствительные данные в словаре.
        
        Args:
            data: Словарь для фильтрации
            
        Returns:
            Словарь с замаскированными чувствительными данными
        """
        result = {}
        for key, value in data.items():
            # Проверяем, является ли ключ чувствительным
            key_lower = key.lower() if isinstance(key, str) else str(key).lower()
            is_sensitive = any(sensitive in key_lower for sensitive in cls.SENSITIVE_FIELDS)
            
            if is_sensitive:
                # Маскируем значение
                result[key] = cls.MASK
            else:
                # Рекурсивно фильтруем значение
                result[key] = cls.filter_sensitive_data(value)
                
        return result
    
    @classmethod
    def _filter_iterable(cls, data: Union[List, tuple, set]) -> Union[List, tuple, set]:
        """
        Фильтрует чувствительные данные в итерируемом объекте.
        
        Args:
            data: Итерируемый объект для фильтрации
            
        Returns:
            Итерируемый объект с замаскированными чувствительными данными
        """
        result = [cls.filter_sensitive_data(item) for item in data]
        
        # Сохраняем исходный тип
        if isinstance(data, tuple):
            return tuple(result)
        if isinstance(data, set):
            return set(result)
        return result
    
    @classmethod
    def _filter_string(cls, data: str) -> str:
        """
        Фильтрует чувствительные данные в строке.
        
        Args:
            data: Строка для фильтрации
            
        Returns:
            Строка с замаскированными чувствительными данными
        """
        if not data:
            return data
        
        # Проверяем, содержит ли строка чувствительные данные по шаблонам
        result = data
        for pattern in cls.SENSITIVE_PATTERNS:
            # Заменяем все совпадения маской
            result = pattern.sub(cls.MASK, result)
        
        # Маскируем пароли в URL
        url_pattern = re.compile(r'(https?://)([^:]+):([^@]+)@')
        result = url_pattern.sub(r'\1\2:***@', result)
        
        return result


def sanitize_payload(payload: Any) -> Any:
    """
    Очищает нагрузку (запросы/ответы) от чувствительной информации.
    
    Args:
        payload: Данные запроса или ответа
        
    Returns:
        Очищенные данные
    """
    # Делаем копию, чтобы не изменять оригинал
    if isinstance(payload, dict):
        payload_copy = copy.deepcopy(payload)
    else:
        payload_copy = payload
    
    # Фильтруем чувствительные данные
    return SensitiveDataFilter.filter_sensitive_data(payload_copy)


def truncate_payload(payload: Any, max_length: int = 1000) -> Any:
    """
    Усекает большие нагрузки для логирования.
    
    Args:
        payload: Данные для логирования
        max_length: Максимальная длина строкового представления
        
    Returns:
        Усеченные данные
    """
    if payload is None:
        return None
    
    # Преобразуем в строку для проверки длины
    payload_str = ""
    try:
        if isinstance(payload, (dict, list)):
            payload_str = json.dumps(payload, ensure_ascii=False)
        else:
            payload_str = str(payload)
    except Exception:
        payload_str = str(type(payload))
    
    # Усекаем, если превышает максимальную длину
    if len(payload_str) > max_length:
        # Для словарей и списков
        if isinstance(payload, dict):
            return {"message": f"Payload truncated (original size: {len(payload_str)})", "keys": list(payload.keys())}
        elif isinstance(payload, list):
            return {"message": f"List truncated (original size: {len(payload_str)})", "count": len(payload)}
        # Для строк
        else:
            return payload_str[:max_length] + f"... [truncated, original size: {len(payload_str)}]"
    
    return payload


def format_query_params(params: Dict[str, Any]) -> str:
    """
    Форматирует параметры запроса для логирования.
    
    Args:
        params: Параметры запроса
        
    Returns:
        Строка с параметрами запроса
    """
    # Очищаем чувствительные данные
    sanitized_params = sanitize_payload(params)
    
    # Форматируем параметры
    if not sanitized_params:
        return ""
    
    # Преобразуем в строку
    try:
        return json.dumps(sanitized_params, ensure_ascii=False)
    except Exception:
        return str(sanitized_params)