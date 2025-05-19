@echo off
echo Активация виртуального окружения...
call venv\Scripts\activate.bat

echo Установка зависимостей...
pip install -r requirements.txt

echo Применение миграций базы данных...
alembic upgrade head

echo Запуск сервера...
uvicorn app.main:app --reload

pause