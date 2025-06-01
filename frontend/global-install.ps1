Write-Host "Installing global dependencies..." -ForegroundColor Yellow
npm install -g vite

Write-Host "Cleaning npm cache..." -ForegroundColor Yellow
npm cache clean --force

Write-Host "Removing node_modules..." -ForegroundColor Yellow
if (Test-Path -Path "node_modules") {
    Remove-Item -Recurse -Force "node_modules"
}

Write-Host "Removing package-lock.json..." -ForegroundColor Yellow
if (Test-Path -Path "package-lock.json") {
    Remove-Item -Force "package-lock.json"
}

Write-Host "Installing dependencies with legacy-peer-deps..." -ForegroundColor Green
npm install --legacy-peer-deps

Write-Host "Installation complete. Run 'npm run dev' to start the development server." -ForegroundColor Cyan
Write-Host "Press any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")