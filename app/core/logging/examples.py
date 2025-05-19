"""
Примеры использования структурированного логирования с контекстом.
"""
import uuid

from app.core.logging import (
    JsonFormatter, ContextLogger, configure_logging, get_logger
)


def example_direct_use():
    """
    Пример прямого использования ContextLogger.
    """
    # Настройка логирования
    configure_logging(log_level="DEBUG", json_format=True)
    
    # Получение экземпляра логгера
    logger = ContextLogger.get_instance()
    
    # Простое логирование
    logger.info("Это информационное сообщение")
    logger.error("Это сообщение об ошибке")
    
    # Логирование с временным контекстом
    user_logger = logger.with_context(user_id="12345")
    user_logger.info("Это сообщение с контекстом пользователя")
    
    # Логирование с несколькими контекстными полями
    request_id = str(uuid.uuid4())
    context_logger = logger.with_context(
        request_id=request_id,
        user_id="12345",
        resource="users",
        action="create"
    )
    context_logger.info("Создание нового пользователя")
    
    # Логирование исключений
    try:
        # Имитируем ошибку
        x = 1 / 0
    except Exception as e:
        context_logger.exception("Произошла ошибка при выполнении операции")
    
    # Установка глобального контекста
    ContextLogger.set_context(
        application="Psybalans",
        environment="development"
    )
    
    # Логирование с глобальным контекстом
    logger.info("Это сообщение включает глобальный контекст")
    
    # Очистка глобального контекста
    ContextLogger.clear_context()


def example_get_logger():
    """
    Пример использования функции get_logger.
    """
    # Настройка логирования
    configure_logging(log_level="INFO", json_format=True)
    
    # Получение логгера с именем модуля
    logger = get_logger("app.services.user")
    logger.info("Сообщение от сервиса пользователей")
    
    # Получение логгера с контекстом
    user_logger = get_logger("app.services.user", user_id="12345", operation="update")
    user_logger.info("Обновление данных пользователя")
    
    # Получение логгера с несколькими контекстными полями
    transaction_logger = get_logger(
        "app.services.payment",
        transaction_id=str(uuid.uuid4()),
        amount=100.50,
        currency="USD",
        user_id="12345"
    )
    transaction_logger.info("Платеж выполнен успешно")


def example_fastapi_integration():
    """
    Пример интеграции с FastAPI (код для справки).
    
    Эта функция представляет пример использования, но не выполняется напрямую.
    """
    # Пример кода для интеграции с FastAPI
    code_example = """
    from fastapi import FastAPI
    from app.core.logging import configure_logging, add_logging_middleware

    app = FastAPI()

    # Настройка логирования
    configure_logging(
        log_level="INFO",
        json_format=True,
        log_file="logs/app.log",
        console_output=True
    )

    # Добавление middleware для логирования запросов
    add_logging_middleware(
        app,
        log_all_requests=True,
        exclude_paths=["/health", "/metrics"],
        request_id_header="X-Request-ID"
    )

    # Теперь все запросы будут автоматически логироваться с контекстом
    # request_id будет автоматически добавлен в заголовки ответа
    """
    print("Пример кода для интеграции с FastAPI:")
    print(code_example)


if __name__ == "__main__":
    # Запуск примеров
    example_direct_use()
    example_get_logger()
    example_fastapi_integration()