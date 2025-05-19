"""
Примеры использования CircuitBreaker для защиты операций с базами данных.
"""
import asyncio
import random
import time
from typing import Dict, List, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.resilience.circuit_breaker import (
    CircuitBreaker, circuit_breaker, CircuitBreakerError, CircuitState
)
from app.core.logging import get_logger

# Логгер для примеров
logger = get_logger("app.examples.circuit_breaker")


# Пример 1: Защита операций с PostgreSQL
class UserDatabaseService:
    """
    Пример сервиса для работы с базой данных, защищенного с помощью CircuitBreaker.
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        
        # Создаем CircuitBreaker для этого сервиса
        self.circuit = CircuitBreaker(
            name="user_database",
            failure_threshold=3,
            recovery_timeout=10.0,
            half_open_max_calls=2,
            call_timeout=5.0
        )
    
    @circuit_breaker(
        name="user_db.get_user",
        failure_threshold=3,
        recovery_timeout=10.0
    )
    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает пользователя по ID с защитой CircuitBreaker.
        """
        # Симуляция возможной ошибки для демонстрации
        if random.random() < 0.3:  # 30% вероятность ошибки
            logger.warning(f"Simulating database error in get_user_by_id for user {user_id}")
            raise Exception("Database connection error")
        
        # Реальный запрос к базе данных
        query = "SELECT * FROM users WHERE id = :user_id"
        result = await self.db.execute(query, {"user_id": user_id})
        user = result.fetchone()
        
        if user:
            return dict(user._mapping)
        return None
    
    # Вариант с использованием CircuitBreaker напрямую как декоратора
    @circuit_breaker(name="user_db.create_user", call_timeout=2.0)
    async def create_user(self, user_data: Dict[str, Any]) -> int:
        """
        Создает пользователя с защитой CircuitBreaker.
        """
        # Симуляция возможной ошибки для демонстрации
        if random.random() < 0.2:  # 20% вероятность ошибки
            logger.warning(f"Simulating database error in create_user")
            raise Exception("Database write error")
        
        # Реальный запрос к базе данных
        query = """
            INSERT INTO users (username, email, password)
            VALUES (:username, :email, :password)
            RETURNING id
        """
        result = await self.db.execute(query, user_data)
        await self.db.commit()
        return result.fetchone()[0]
    
    # Вариант с использованием CircuitBreaker с функцией обратного вызова
    async def update_user(self, user_id: int, user_data: Dict[str, Any]) -> bool:
        """
        Обновляет пользователя с защитой CircuitBreaker и обработкой ошибок.
        """
        # Проверяем, разрешен ли запрос
        if not self.circuit.allow_request():
            logger.warning(
                f"Circuit {self.circuit.name} is {self.circuit.state.value}, update_user rejected"
            )
            return False
        
        try:
            # Симуляция возможной ошибки для демонстрации
            if random.random() < 0.25:  # 25% вероятность ошибки
                logger.warning(f"Simulating database error in update_user for user {user_id}")
                raise Exception("Database update error")
            
            # Реальный запрос к базе данных
            query = """
                UPDATE users
                SET username = :username, email = :email
                WHERE id = :user_id
            """
            params = {**user_data, "user_id": user_id}
            await self.db.execute(query, params)
            await self.db.commit()
            
            # Регистрируем успешное выполнение
            self.circuit._record_success()
            return True
            
        except Exception as e:
            # Регистрируем ошибку
            self.circuit._record_failure(e)
            logger.error(f"Error updating user {user_id}: {str(e)}")
            return False


# Пример 2: Защита операций с MongoDB
class ActivityRepository:
    """
    Пример репозитория MongoDB с защитой CircuitBreaker.
    """
    
    def __init__(self, client: AsyncIOMotorClient, database_name: str):
        self.client = client
        self.db = client[database_name]
        self.collection = self.db.activities
    
    @circuit_breaker(
        name="mongodb.activities.get",
        failure_threshold=5,
        recovery_timeout=15.0,
        half_open_max_calls=3
    )
    async def get_activity_by_id(self, activity_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает активность по ID с защитой CircuitBreaker.
        """
        # Симуляция возможной ошибки для демонстрации
        if random.random() < 0.15:  # 15% вероятность ошибки
            logger.warning(f"Simulating MongoDB error in get_activity_by_id")
            await asyncio.sleep(0.1)  # Симуляция задержки
            raise Exception("MongoDB connection timeout")
        
        # Реальный запрос к MongoDB
        return await self.collection.find_one({"_id": activity_id})
    
    @circuit_breaker(
        name="mongodb.activities.create",
        failure_threshold=4,
        recovery_timeout=20.0
    )
    async def create_activity(self, activity_data: Dict[str, Any]) -> str:
        """
        Создает активность с защитой CircuitBreaker.
        """
        # Симуляция возможной ошибки для демонстрации
        if random.random() < 0.1:  # 10% вероятность ошибки
            logger.warning(f"Simulating MongoDB error in create_activity")
            raise Exception("MongoDB write error")
        
        # Реальный запрос к MongoDB
        result = await self.collection.insert_one(activity_data)
        return str(result.inserted_id)


# Пример 3: Демонстрация работы CircuitBreaker в различных состояниях
async def demo_circuit_breaker_states():
    """
    Демонстрирует работу CircuitBreaker в различных состояниях.
    """
    # Создаем CircuitBreaker с настройками для демонстрации
    cb = CircuitBreaker(
        name="demo_circuit",
        failure_threshold=3,     # После 3 ошибок переходим в OPEN
        recovery_timeout=5.0,    # После 5 секунд переходим в HALF_OPEN
        half_open_max_calls=2    # В HALF_OPEN разрешаем 2 запроса
    )
    
    # Функция, имитирующая операцию с вероятностью ошибки
    async def test_operation(fail_probability: float = 0.0) -> str:
        if random.random() < fail_probability:
            raise Exception("Simulated operation error")
        await asyncio.sleep(0.1)  # Имитация работы
        return "Operation successful"
    
    # 1. Демонстрация состояния CLOSED
    logger.info("Starting in CLOSED state...")
    for i in range(5):
        try:
            # Успешные операции в CLOSED
            if cb.allow_request():
                result = await test_operation(0.0)  # Без ошибок
                cb._record_success()
                logger.info(f"Request {i+1} succeeded: {result}")
        except Exception as e:
            cb._record_failure(e)
            logger.error(f"Request {i+1} failed: {str(e)}")
    
    # 2. Демонстрация перехода в OPEN после ошибок
    logger.info("\nGenerating failures to transition to OPEN state...")
    for i in range(5):
        try:
            if cb.allow_request():
                result = await test_operation(0.8)  # 80% вероятность ошибки
                cb._record_success()
                logger.info(f"Request {i+1} succeeded")
            else:
                logger.info(f"Request {i+1} rejected (Circuit is {cb.state.value})")
        except Exception as e:
            cb._record_failure(e)
            logger.error(f"Request {i+1} failed: {str(e)}")
    
    # Проверяем, что цепь открыта
    if cb.state == CircuitState.OPEN:
        logger.info(f"Circuit is now OPEN after {cb.failures} failures")
    
    # 3. Демонстрация отклонения запросов в состоянии OPEN
    logger.info("\nAttempting requests while circuit is OPEN...")
    for i in range(3):
        try:
            if cb.allow_request():
                result = await test_operation()
                cb._record_success()
                logger.info(f"Request succeeded")
            else:
                logger.info(f"Request rejected (Circuit is {cb.state.value})")
        except CircuitBreakerError as e:
            logger.error(f"CircuitBreakerError: {str(e)}")
    
    # 4. Ждем перехода в HALF_OPEN
    logger.info(f"\nWaiting {cb.recovery_timeout} seconds for HALF_OPEN state...")
    await asyncio.sleep(cb.recovery_timeout + 0.1)
    
    # Проверяем, что цепь в полуоткрытом состоянии
    if cb.state == CircuitState.HALF_OPEN:
        logger.info("Circuit is now HALF_OPEN")
    
    # 5. Демонстрация работы в HALF_OPEN
    logger.info("\nTesting in HALF_OPEN state...")
    for i in range(5):
        try:
            if cb.allow_request():
                # В HALF_OPEN делаем успешные запросы для перехода в CLOSED
                result = await test_operation(0.0)  # Без ошибок
                cb._record_success()
                logger.info(f"Request {i+1} succeeded in HALF_OPEN state")
            else:
                logger.info(f"Request {i+1} rejected (Circuit is {cb.state.value})")
        except Exception as e:
            cb._record_failure(e)
            logger.error(f"Request {i+1} failed in HALF_OPEN state: {str(e)}")
    
    # Проверяем, вернулись ли в закрытое состояние
    logger.info(f"\nFinal circuit state: {cb.state.value}")
    
    return "Demo completed"


# Пример запуска демонстрации
async def run_examples():
    """
    Запускает примеры использования CircuitBreaker.
    """
    # Запускаем демонстрацию смены состояний
    await demo_circuit_breaker_states()


if __name__ == "__main__":
    asyncio.run(run_examples())