# Скрипт для поиска других компонентов, использующих keyframes
Write-Host "Проверка других компонентов на наличие неправильного импорта keyframes..." -ForegroundColor Yellow

$files = Get-ChildItem -Path "src" -Recurse -Filter "*.tsx" | Where-Object { $_.FullName -ne "src\components\MobileMenu.tsx" }
$problemFiles = @()

foreach ($file in $files) {
    $content = Get-Content -Path $file.FullName -Raw
    if ($content -match "import.*keyframes.*from\s+['\""]@chakra-ui/react['\""]\s*;") {
        $problemFiles += $file.FullName
    }
}

if ($problemFiles.Count -gt 0) {
    Write-Host "Найдены файлы с неправильным импортом keyframes:" -ForegroundColor Red
    foreach ($file in $problemFiles) {
        Write-Host "  - $file" -ForegroundColor Red
    }
    Write-Host "Рекомендуется заменить импорт keyframes с '@chakra-ui/react' на '@emotion/react'" -ForegroundColor Yellow
} else {
    Write-Host "Не найдено других компонентов с неправильным импортом keyframes" -ForegroundColor Green
}

Write-Host "Нажмите любую клавишу для продолжения..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")