"""
Пакет, содержащий компоненты для обеспечения отказоустойчивости приложения.
"""

from app.core.resilience.circuit_breaker import (
    CircuitBreaker, circuit_breaker, CircuitBreakerError, CircuitState
)

__all__ = [
    "CircuitBreaker",
    "circuit_breaker",
    "CircuitBreakerError",
    "CircuitState"
]