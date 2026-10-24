@echo off
setlocal
cd /d "%~dp0"

where uv >nul 2>&1
if errorlevel 1 (
    echo uv is required. Install it from https://docs.astral.sh/uv/getting-started/installation/
    goto :error
)
where npm >nul 2>&1
if errorlevel 1 (
    echo Node.js 24 LTS and npm are required. Install them from https://nodejs.org/
    goto :error
)

echo Checking backend dependencies...
pushd backend
call uv sync --locked
if errorlevel 1 (
    popd
    goto :error
)
popd

if not exist "frontend\node_modules\" (
    echo Installing frontend dependencies...
    pushd frontend
    call npm ci
    if errorlevel 1 (
        popd
        goto :error
    )
    popd
)

rem Use the local API through Vite's existing proxy, even with other .env settings.
set "VITE_API_BASE_URL=/api"
set "VITE_DEMO_MODE=false"
set "CARECOMPASS_API_TARGET=http://127.0.0.1:8000"

start "CareCompass Backend" /D "%~dp0backend" cmd /d /k "uv run --locked uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
start "CareCompass Frontend" /D "%~dp0frontend" cmd /d /k "npm run dev -- --open"
echo Frontend: http://127.0.0.1:5173
echo API docs: http://127.0.0.1:8000/docs
echo To stop, press Ctrl+C in each server window and close it.
exit /b 0

:error
echo.
echo CareCompass could not start. Fix the error above and try again.
pause
exit /b 1
