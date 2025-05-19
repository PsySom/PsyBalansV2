# Работа с базами данных в PsyBalans

Приложение PsyBalans использует полиглотную архитектуру хранения данных с тремя основными базами данных:

1. **PostgreSQL** - для структурированных данных (пользователи, активности, календарь, потребности)
2. **MongoDB** - для полуструктурированных данных (дневники, записи настроения, мысли)
3. **Redis** - для кэширования и обмена сообщениями

## Конфигурация

Конфигурация баз данных осуществляется через `.env` файл, пример которого находится в `.env.example`.

### PostgreSQL

Настройка PostgreSQL может быть выполнена двумя способами:

```
# Вариант 1: через отдельные параметры
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=psybalans

# Вариант 2: через строку подключения
DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/psybalans
```

### MongoDB

```
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=psybalans
```

### Redis

```
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
# Или используйте полный URL
REDIS_URL=redis://localhost:6379/0
```

## Использование в коде

### PostgreSQL (SQLAlchemy)

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

@app.get("/users")
async def get_users(db: AsyncSession = Depends(get_db)):
    # Выполнение запроса
    result = await db.execute("SELECT * FROM users")
    users = result.all()
    return users
```

### MongoDB (Motor)

```python
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_mongodb

@app.get("/mood-entries")
async def get_mood_entries(db: AsyncIOMotorDatabase = Depends(get_mongodb)):
    # Получение документов из коллекции
    cursor = db.mood_entries.find({"user_id": "some_id"})
    entries = await cursor.to_list(length=100)
    return entries
```

Или с использованием вспомогательных функций:

```python
from app.core.database import find_many

@app.get("/mood-entries")
async def get_mood_entries():
    entries = await find_many(
        collection_name="mood_entries",
        query={"user_id": "some_id"},
        skip=0,
        limit=100,
        sort_by={"timestamp": -1}
    )
    return entries
```

### Redis

```python
from fastapi import Depends
from redis.asyncio import Redis
from app.core.database import get_redis

@app.get("/cached-data")
async def get_cached_data(redis: Redis = Depends(get_redis)):
    # Получение данных из кэша
    data = await redis.get("cache_key")
    if not data:
        # Если данных нет в кэше, получаем их и сохраняем
        data = get_expensive_data()
        await redis.set("cache_key", data, ex=3600)  # Кэш на 1 час
    return data
```

Или с использованием вспомогательных функций:

```python
from app.core.database import get_cache, set_cache

@app.get("/cached-data")
async def get_cached_data():
    # Проверяем кэш
    data = await get_cache("expensive_operation")
    if not data:
        # Если данных нет в кэше, получаем их и сохраняем
        data = get_expensive_data()
        await set_cache("expensive_operation", data, 3600)  # Кэш на 1 час
    return data
```

## Миграции базы данных PostgreSQL

Для миграций используется Alembic с поддержкой асинхронной SQLAlchemy.

### Использование скрипта-помощника

В проекте есть удобный скрипт-помощник `migrations.py` для управления миграциями:

```bash
# Применить все миграции
./migrations.py upgrade

# Автоматически сгенерировать миграцию на основе изменений моделей
./migrations.py create --name "описание_изменений" --autogenerate

# Создать пустую миграцию для ручного написания
./migrations.py create --name "описание_изменений"

# Откатить на одну миграцию назад
./migrations.py downgrade --revision -1

# Показать историю миграций
./migrations.py history

# Проверить текущую версию
./migrations.py current

# Проверить, какие миграции будут сгенерированы (без создания файлов)
./migrations.py check
```

### Прямое использование Alembic

Вы также можете использовать Alembic напрямую:

```bash
# Создание новой миграции
alembic revision --autogenerate -m "описание миграции"

# Применение миграций
alembic upgrade head

# На одну версию назад
alembic downgrade -1

# До определенной версии
alembic downgrade <revision_id>
```

### Асинхронная поддержка

Система миграций настроена для работы с асинхронной SQLAlchemy и правильно поддерживает все модели приложения. При изменении моделей миграции будут автоматически учитывать эти изменения при использовании флага `--autogenerate`.

## Проверка подключений

Приложение предоставляет API для проверки состояния подключений к базам данных:

```
GET /api/status
```

Этот эндпоинт возвращает статус подключения к каждой базе данных.