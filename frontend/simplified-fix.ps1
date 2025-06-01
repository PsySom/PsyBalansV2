# Упрощенный скрипт для починки проекта
Write-Host "Удаление node_modules и package-lock.json..." -ForegroundColor Yellow
if (Test-Path -Path "node_modules") {
    Remove-Item -Recurse -Force "node_modules"
}
if (Test-Path -Path "package-lock.json") {
    Remove-Item -Force "package-lock.json"
}

# Создаем новый package.json с минимальными требованиями
$packageJson = @{
    name = "frontend"
    private = $true
    version = "0.0.0"
    type = "module"
    scripts = @{
        dev = "vite"
        build = "tsc -b && vite build"
        lint = "eslint ."
        preview = "vite preview"
    }
    dependencies = @{
        "@chakra-ui/react" = "^2.8.0"
        "@emotion/react" = "^11.11.0"
        "@emotion/styled" = "^11.11.0"
        "framer-motion" = "^10.12.16"
        "react" = "^18.2.0"
        "react-dom" = "^18.2.0"
        "react-router-dom" = "^6.14.0"
        "zustand" = "^4.4.0"
    }
    devDependencies = @{
        "@types/react" = "^18.2.15"
        "@types/react-dom" = "^18.2.7"
        "@vitejs/plugin-react" = "^4.0.3"
        "eslint" = "^8.45.0"
        "typescript" = "~5.0.4"
        "vite" = "^4.4.5"
    }
}

# Сохраняем старый package.json
Rename-Item -Path "package.json" -NewName "package.json.backup"

# Записываем новый package.json
$packageJson | ConvertTo-Json -Depth 10 | Set-Content -Path "package.json"

Write-Host "Установка минимальных зависимостей..." -ForegroundColor Green
npm install

Write-Host "Установка завершена. Запустите npm run dev для запуска сервера разработки" -ForegroundColor Green
Write-Host "Нажмите любую клавишу для продолжения..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")