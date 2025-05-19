"""
Middleware для автоматического добавления контекста запроса в логи.
"""
import time
import uuid
from typing import Callable, Optional

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.core.logging.context_logger import ContextLogger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware для автоматического добавления контекста запроса в логи
    и логирования информации о запросах.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        log_all_requests: bool = True,
        exclude_paths: Optional[list[str]] = None,
        request_id_header: str = "X-Request-ID",
    ):
        """
        Инициализирует middleware.
        
        Args:
            app: ASGI приложение
            log_all_requests: Логировать ли все запросы (иначе только ошибки)
            exclude_paths: Пути, которые не будут логироваться (например, /health)
            request_id_header: Заголовок для идентификатора запроса
        """
        super().__init__(app)
        self.log_all_requests = log_all_requests
        self.exclude_paths = exclude_paths or ["/healthcheck", "/health", "/metrics"]
        self.request_id_header = request_id_header
        self.logger = ContextLogger.get_instance(logger_name="app.request")
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Обрабатывает запрос, добавляя контекст в логи.
        
        Args:
            request: HTTP запрос
            call_next: Функция для продолжения обработки запроса
            
        Returns:
            HTTP ответ
        """
        # Проверяем, нужно ли обрабатывать этот путь
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Получаем или генерируем request_id
        request_id = request.headers.get(self.request_id_header)
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # Устанавливаем базовый контекст запроса
        request_context = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("User-Agent"),
        }
        
        # Если есть пользователь, добавляем его в контекст
        user = getattr(request.state, "user", None)
        if user and hasattr(user, "id"):
            request_context["user_id"] = str(user.id)
        
        # Устанавливаем контекст
        ContextLogger.set_context(**request_context)
        
        # Засекаем время начала обработки запроса
        start_time = time.time()
        
        try:
            # Добавляем request_id в заголовки ответа
            response = await call_next(request)
            
            # Вычисляем время обработки запроса
            process_time = time.time() - start_time
            request_context["duration"] = round(process_time * 1000, 2)  # в миллисекундах
            request_context["status_code"] = response.status_code
            
            # Логируем информацию о запросе, если нужно
            if self.log_all_requests or response.status_code >= 400:
                log_method = self.logger.info if response.status_code < 400 else self.logger.warning
                log_method(
                    f"{request.method} {request.url.path} completed with status {response.status_code}",
                    extra=request_context
                )
            
            # Добавляем request_id в заголовки ответа
            response.headers[self.request_id_header] = request_id
            return response
            
        except Exception as e:
            # В случае ошибки логируем информацию и пробрасываем исключение дальше
            process_time = time.time() - start_time
            request_context["duration"] = round(process_time * 1000, 2)
            request_context["error_type"] = type(e).__name__
            
            self.logger.exception(
                f"Error processing request {request.method} {request.url.path}: {str(e)}",
                extra=request_context
            )
            raise
        finally:
            # Очищаем контекст в конце обработки запроса
            ContextLogger.clear_context()


def add_logging_middleware(
    app: FastAPI,
    log_all_requests: bool = True,
    exclude_paths: Optional[list[str]] = None,
    request_id_header: str = "X-Request-ID",
) -> None:
    """
    Добавляет middleware для логирования запросов к FastAPI приложению.
    
    Args:
        app: FastAPI приложение
        log_all_requests: Логировать ли все запросы (иначе только ошибки)
        exclude_paths: Пути, которые не будут логироваться
        request_id_header: Заголовок для идентификатора запроса
    """
    app.add_middleware(
        RequestLoggingMiddleware,
        log_all_requests=log_all_requests,
        exclude_paths=exclude_paths,
        request_id_header=request_id_header,
    )