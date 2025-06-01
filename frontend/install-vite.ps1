# Создание нового проекта и копирование исходных файлов
Write-Host "Создание нового проекта Vite..." -ForegroundColor Yellow

# Создаем временную директорию
$tempDir = "C:\temp\vite-temp"
if (Test-Path $tempDir) {
    Remove-Item -Recurse -Force $tempDir
}
New-Item -ItemType Directory -Path $tempDir | Out-Null

# Переходим во временную директорию
Set-Location $tempDir

# Создаем новый проект Vite с React и TypeScript
Write-Host "Инициализация нового проекта Vite с React и TypeScript..." -ForegroundColor Cyan
npm create vite@latest temp-app -- --template react-ts

# Копируем исходные файлы из временного проекта
Write-Host "Копирование файлов конфигурации..." -ForegroundColor Cyan
$currentDir = "C:\Users\somov\OneDrive\Рабочий стол\PsyBalansV2\frontend"
Copy-Item -Path "$tempDir\temp-app\vite.config.ts" -Destination "$currentDir"
Copy-Item -Path "$tempDir\temp-app\tsconfig.json" -Destination "$currentDir"
Copy-Item -Path "$tempDir\temp-app\tsconfig.node.json" -Destination "$currentDir"
Copy-Item -Path "$tempDir\temp-app\package.json" -Destination "$currentDir\package.json.new"

# Возвращаемся в исходную директорию
Set-Location $currentDir

Write-Host "Внесение изменений в package.json..." -ForegroundColor Yellow
# Читаем содержимое обоих package.json
$originalContent = Get-Content -Path "package.json" -Raw | ConvertFrom-Json
$newContent = Get-Content -Path "package.json.new" -Raw | ConvertFrom-Json

# Сохраняем оригинальные зависимости
$originalDependencies = $originalContent.dependencies
$originalDevDependencies = $originalContent.devDependencies

# Обновляем новый package.json с именем и версией из оригинального
$newContent.name = $originalContent.name
$newContent.version = $originalContent.version
$newContent.private = $originalContent.private

# Объединяем зависимости
foreach($prop in $originalDependencies.PSObject.Properties) {
    if(-not $newContent.dependencies.PSObject.Properties[$prop.Name]) {
        $newContent.dependencies | Add-Member -MemberType NoteProperty -Name $prop.Name -Value $prop.Value
    }
}

# Объединяем dev зависимости
foreach($prop in $originalDevDependencies.PSObject.Properties) {
    if(-not $newContent.devDependencies.PSObject.Properties[$prop.Name]) {
        $newContent.devDependencies | Add-Member -MemberType NoteProperty -Name $prop.Name -Value $prop.Value
    }
}

# Сохраняем обновленный package.json
$newContent | ConvertTo-Json -Depth 10 | Set-Content -Path "package.json.updated"

# Удаляем временный package.json
Remove-Item -Path "package.json.new"

Write-Host "Переименование старого package.json и установка нового..." -ForegroundColor Yellow
Rename-Item -Path "package.json" -NewName "package.json.old"
Rename-Item -Path "package.json.updated" -NewName "package.json"

Write-Host "Удаление node_modules и установка зависимостей..." -ForegroundColor Yellow
if (Test-Path -Path "node_modules") {
    Remove-Item -Recurse -Force "node_modules"
}
if (Test-Path -Path "package-lock.json") {
    Remove-Item -Force "package-lock.json"
}

# Устанавливаем зависимости
npm install --legacy-peer-deps

Write-Host "Установка завершена. Запустите npm run dev для запуска сервера разработки" -ForegroundColor Green
Write-Host "Нажмите любую клавишу для продолжения..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")