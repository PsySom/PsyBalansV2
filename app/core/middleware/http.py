"""
HTTP middleware для структурированного логирования запросов и ответов.
"""
import asyncio
import json
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Set, Union, cast

import fastapi
from fastapi import FastAPI, Request, Response
from fastapi.routing import APIRoute
from starlette.background import BackgroundTask
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import get_logger
from app.core.middleware.utils import sanitize_payload, truncate_payload, format_query_params


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware для логирования HTTP запросов и ответов.
    
    Отслеживает входящие запросы и исходящие ответы FastAPI,
    измеряет время выполнения и логирует детали в структурированном формате.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        log_all_requests: bool = True,
        log_request_body: bool = True,
        log_response_body: bool = True,
        exclude_paths: Optional[List[str]] = None,
        exclude_extensions: Optional[List[str]] = None,
        max_body_length: int = 10000,
        slow_request_threshold: float = 1.0,
        request_id_header: str = "X-Request-ID"
    ):
        """
        Инициализация middleware для логирования HTTP запросов и ответов.
        
        Args:
            app: ASGI приложение
            log_all_requests: Логировать ли все запросы (иначе только ошибки)
            log_request_body: Логировать ли тело запроса
            log_response_body: Логировать ли тело ответа
            exclude_paths: Пути, которые не будут логироваться (например, /health)
            exclude_extensions: Расширения файлов, которые не будут логироваться
            max_body_length: Максимальная длина тела для логирования
            slow_request_threshold: Порог времени выполнения для медленных запросов (в секундах)
            request_id_header: Заголовок для идентификатора запроса
        """
        super().__init__(app)
        self.log_all_requests = log_all_requests
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.exclude_paths = exclude_paths or ["/healthcheck", "/health", "/metrics", "/openapi.json", "/docs", "/redoc"]
        self.exclude_extensions = exclude_extensions or [".js", ".css", ".ico", ".png", ".jpg", ".svg", ".woff", ".woff2"]
        self.max_body_length = max_body_length
        self.slow_request_threshold = slow_request_threshold
        self.request_id_header = request_id_header
        
        self.logger = get_logger("app.http")
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Обрабатывает запрос, логируя информацию о запросе и ответе.
        
        Args:
            request: HTTP запрос
            call_next: Функция для продолжения обработки запроса
            
        Returns:
            HTTP ответ
        """
        # Проверяем, нужно ли обрабатывать этот путь
        if self._should_skip_logging(request):
            return await call_next(request)
        
        # Получаем или генерируем request_id
        request_id = request.headers.get(self.request_id_header)
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # Засекаем время начала обработки запроса
        start_time = time.time()
        
        # Создаем контекст для логирования запроса
        request_context = await self._build_request_context(request, request_id)
        
        # Логируем начало обработки запроса
        self.logger.info(
            f"HTTP {request.method} {request.url.path} - Started",
            extra=request_context
        )
        
        # Модифицируем ответ для логирования
        response = await self._process_response(request, call_next, start_time, request_id, request_context)
        
        return response
    
    def _should_skip_logging(self, request: Request) -> bool:
        """
        Проверяет, нужно ли пропустить логирование для данного запроса.
        
        Args:
            request: HTTP запрос
            
        Returns:
            True, если логирование нужно пропустить
        """
        # Проверяем пути, которые нужно исключить
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return True
        
        # Проверяем расширения, которые нужно исключить
        if any(request.url.path.endswith(ext) for ext in self.exclude_extensions):
            return True
        
        return False
    
    async def _build_request_context(self, request: Request, request_id: str) -> Dict[str, Any]:
        """
        Создает контекст для логирования запроса.
        
        Args:
            request: HTTP запрос
            request_id: Идентификатор запроса
            
        Returns:
            Словарь с контекстом для логирования
        """
        # Базовый контекст
        context = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": format_query_params(dict(request.query_params)),
            "client_ip": self._get_client_ip(request),
        }
        
        # Добавляем заголовки (фильтруем чувствительные данные)
        headers = dict(request.headers.items())
        context["headers"] = sanitize_payload(headers)
        
        # Добавляем информацию о пользователе, если доступна
        user = getattr(request.state, "user", None)
        if user:
            if hasattr(user, "id"):
                context["user_id"] = str(user.id)
            if hasattr(user, "username"):
                context["username"] = user.username
        
        # Добавляем тело запроса, если нужно
        if self.log_request_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                # Читаем тело запроса
                body = await self._read_body(request)
                if body:
                    # Фильтруем и усекаем тело
                    context["body"] = truncate_payload(
                        sanitize_payload(body),
                        self.max_body_length
                    )
            except Exception as e:
                context["body_error"] = f"Error reading request body: {str(e)}"
        
        return context
    
    async def _process_response(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
        start_time: float,
        request_id: str,
        request_context: Dict[str, Any]
    ) -> Response:
        """
        Обрабатывает ответ, логируя информацию о нем.
        
        Args:
            request: HTTP запрос
            call_next: Функция для продолжения обработки запроса
            start_time: Время начала обработки запроса
            request_id: Идентификатор запроса
            request_context: Контекст запроса для логирования
            
        Returns:
            HTTP ответ
        """
        try:
            # Вызываем следующий middleware в цепочке
            response = await call_next(request)
            
            # Вычисляем время выполнения
            duration = time.time() - start_time
            
            # Создаем контекст для логирования ответа
            response_context = {
                "request_id": request_id,
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 2),
                "headers": sanitize_payload(dict(response.headers.items()))
            }
            
            # Добавляем тело ответа, если нужно и если запрос успешный
            if self.log_response_body and 200 <= response.status_code < 300:
                response_body = await self._get_response_body(response)
                if response_body:
                    response_context["body"] = truncate_payload(
                        sanitize_payload(response_body),
                        self.max_body_length
                    )
            
            # Определяем уровень логирования и сообщение
            log_level = "info"
            is_slow = duration >= self.slow_request_threshold
            
            if response.status_code >= 500:
                log_level = "error"
            elif response.status_code >= 400:
                log_level = "warning"
            elif is_slow:
                log_level = "warning"
                response_context["slow_request"] = True
            
            # Формируем сообщение
            message = f"HTTP {request.method} {request.url.path} - Completed with status {response.status_code}"
            if is_slow:
                message = f"SLOW REQUEST: {message}"
            
            # Логируем информацию о запросе и ответе
            if log_level == "info":
                if self.log_all_requests:
                    self.logger.info(message, extra=response_context)
            elif log_level == "warning":
                self.logger.warning(message, extra=response_context)
            elif log_level == "error":
                self.logger.error(message, extra=response_context)
            
            # Добавляем request_id в заголовки ответа
            response.headers[self.request_id_header] = request_id
            
            return response
            
        except Exception as e:
            # В случае ошибки логируем информацию и пробрасываем исключение дальше
            duration = time.time() - start_time
            
            error_context = {
                "request_id": request_id,
                "duration_ms": round(duration * 1000, 2),
                "error_type": type(e).__name__,
                "error_message": str(e),
            }
            
            self.logger.error(
                f"HTTP {request.method} {request.url.path} - Error: {error_context['error_type']}",
                extra=error_context,
                exc_info=True
            )
            
            raise
    
    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """
        Получает IP-адрес клиента из запроса.
        
        Args:
            request: HTTP запрос
            
        Returns:
            IP-адрес клиента
        """
        # Проверяем заголовки X-Forwarded-For, X-Real-IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # X-Forwarded-For может содержать несколько IP через запятую
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Если заголовки отсутствуют, используем информацию из request.client
        if request.client and hasattr(request.client, "host"):
            return request.client.host
        
        return "unknown"
    
    async def _read_body(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Читает тело запроса.
        
        Args:
            request: HTTP запрос
            
        Returns:
            Словарь с данными тела запроса или None
        """
        try:
            body = await request.json()
            return body
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            # Если не JSON, пробуем прочитать как форму
            try:
                form = await request.form()
                return {key: value for key, value in form.items()}
            except Exception:
                # Если и это не удалось, пробуем прочитать как обычное тело
                try:
                    body = await request.body()
                    return {"raw": body.decode("utf-8", errors="replace")}
                except Exception:
                    return None
    
    async def _get_response_body(self, response: Response) -> Optional[Dict[str, Any]]:
        """
        Получает тело ответа.
        
        Args:
            response: HTTP ответ
            
        Returns:
            Данные тела ответа или None
        """
        # Проверяем, есть ли у ответа тело
        if not hasattr(response, "body"):
            return None
        
        try:
            # Пробуем декодировать как JSON
            body = response.body.decode("utf-8")
            return json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            # Если не JSON, возвращаем как текст
            try:
                return {"raw": response.body.decode("utf-8", errors="replace")}
            except Exception:
                return None


def add_logging_middleware(
    app: FastAPI,
    log_all_requests: bool = True,
    log_request_body: bool = True,
    log_response_body: bool = True,
    exclude_paths: Optional[List[str]] = None,
    exclude_extensions: Optional[List[str]] = None,
    max_body_length: int = 10000,
    slow_request_threshold: float = 1.0,
    request_id_header: str = "X-Request-ID"
) -> None:
    """
    Добавляет middleware для логирования HTTP запросов и ответов к FastAPI приложению.
    
    Args:
        app: FastAPI приложение
        log_all_requests: Логировать ли все запросы (иначе только ошибки)
        log_request_body: Логировать ли тело запроса
        log_response_body: Логировать ли тело ответа
        exclude_paths: Пути, которые не будут логироваться
        exclude_extensions: Расширения файлов, которые не будут логироваться
        max_body_length: Максимальная длина тела для логирования
        slow_request_threshold: Порог времени выполнения для медленных запросов
        request_id_header: Заголовок для идентификатора запроса
    """
    app.add_middleware(
        LoggingMiddleware,
        log_all_requests=log_all_requests,
        log_request_body=log_request_body,
        log_response_body=log_response_body,
        exclude_paths=exclude_paths,
        exclude_extensions=exclude_extensions,
        max_body_length=max_body_length,
        slow_request_threshold=slow_request_threshold,
        request_id_header=request_id_header
    )