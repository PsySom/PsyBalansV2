@echo off
echo Cleaning npm cache...
npm cache clean --force

echo Removing node_modules...
if exist node_modules rmdir /s /q node_modules

echo Removing package-lock.json...
if exist package-lock.json del package-lock.json

echo Installing dependencies with legacy-peer-deps...
npm install --legacy-peer-deps

echo Installation complete. Run "npm run dev" to start the development server.
pause