@echo off
echo Удаление node_modules и package-lock.json...
rmdir /s /q node_modules
del package-lock.json

echo Установка rollup глобально...
npm install -g rollup

echo Установка зависимостей...
npm install --legacy-peer-deps
npm install @rollup/rollup-win32-x64-msvc --no-save

echo Готово! Запустите npm run dev для старта сервера разработки
pause