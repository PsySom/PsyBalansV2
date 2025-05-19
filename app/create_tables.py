import asyncio
import logging
import os
import sys
from sqlalchemy import JSON, Column, MetaData, Table

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Функция для создания всех таблиц с использованием SQLite
async def create_tables():
    try:
        # Импортируем модели и настройки
        from sqlalchemy.ext.asyncio import create_async_engine
        from app.models.base import Base
        # Импортируем все модели, чтобы они были доступны для SQLAlchemy
        from app.models.user import User
        from app.models.activity import Activity
        from app.models.activity_types import ActivityType, ActivitySubtype
        from app.models.needs import Need, NeedCategory
        from app.models.user_needs import UserNeed
        from app.models.calendar import UserCalendar, ActivitySchedule
        
        logger.info("Начинаем создание таблиц в SQLite...")
        
        # Создаем временную базу данных SQLite
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "psybalans.db")
        logger.info(f"Путь к базе данных SQLite: {db_path}")
        
        # Исправляем проблему с JSONB типом
        metadata = MetaData()
        # Для каждой модели с JSONB полем, мы создадим свою таблицу с JSON типом
        
        # Создаем движок SQLite
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{db_path}",
            echo=True,
            connect_args={"check_same_thread": False}
        )
        
        # Создаем таблицы по одной, вместо использования create_all
        async with engine.begin() as conn:
            # Создаем модели, которые не используют JSONB
            # Подход 1: Использовать reflection для обнаружения таблиц, которые можно создать
            import inspect
            from sqlalchemy import inspect as sa_inspect
            
            # Создадим список таблиц, которые можно безопасно создать
            tables_to_create = []
            for class_name, cls in inspect.getmembers(sys.modules["app.models.user"], inspect.isclass):
                if issubclass(cls, Base) and cls != Base:
                    try:
                        # Проверяем на наличие JSONB типов
                        for column in sa_inspect(cls).columns:
                            if str(column.type).upper() == 'JSONB':
                                logger.warning(f"Модель {cls.__name__} содержит JSONB поле {column.name}, "
                                              f"которое не поддерживается SQLite")
                                break
                        else:
                            tables_to_create.append(cls.__table__)
                    except Exception as e:
                        logger.error(f"Ошибка при проверке модели {cls.__name__}: {e}")
            
            # Создаем отдельные таблицы, которые не содержат JSONB
            for table in tables_to_create:
                try:
                    await conn.run_sync(lambda sync_conn: table.create(sync_conn, checkfirst=True))
                    logger.info(f"Таблица {table.name} создана успешно")
                except Exception as e:
                    logger.error(f"Ошибка при создании таблицы {table.name}: {e}")
            
        logger.info("Создание таблиц завершено!")
        return True
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц: {e}")
        # Выводим полный стек ошибки для отладки
        import traceback
        logger.error(traceback.format_exc())
        return False

# Запускаем функцию создания таблиц
if __name__ == "__main__":
    # Настраиваем вывод более подробных логов для отладки
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    asyncio.run(create_tables())