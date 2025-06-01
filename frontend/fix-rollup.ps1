Write-Host "Удаление node_modules и package-lock.json..." -ForegroundColor Yellow
if (Test-Path -Path "node_modules") {
    Remove-Item -Recurse -Force "node_modules"
}
if (Test-Path -Path "package-lock.json") {
    Remove-Item -Force "package-lock.json"
}

Write-Host "Установка rollup глобально..." -ForegroundColor Yellow
npm install -g rollup

Write-Host "Установка зависимостей..." -ForegroundColor Green
npm install --legacy-peer-deps
npm install @rollup/rollup-win32-x64-msvc --no-save

Write-Host "Понижение версии vite до стабильной..." -ForegroundColor Green
npm uninstall vite
npm install vite@4.5.1 --save-dev

Write-Host "Готово! Запустите npm run dev для старта сервера разработки" -ForegroundColor Cyan
Write-Host "Нажмите любую клавишу для продолжения..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")