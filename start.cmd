@echo off

echo.
echo Restoring backend python packages
echo.
call python -m pip install -r requirements.txt
if "%errorlevel%" neq "0" (
    echo Failed to restore backend python packages
    exit /B %errorlevel%
)

REM Load UI_URL_PREFIX from .env if it exists (before changing directory)
if exist .env (
    for /f "usebackq tokens=1,* delims==" %%a in (.env) do (
        if "%%a"=="UI_URL_PREFIX" set "UI_URL_PREFIX=%%b"
    )
)

echo.
echo Restoring frontend npm packages
echo.
cd frontend
call npm install
if "%errorlevel%" neq "0" (
    echo Failed to restore frontend npm packages
    exit /B %errorlevel%
)

echo.
echo Building frontend
echo.
REM Set VITE_URL_PREFIX to match UI_URL_PREFIX for frontend build
if defined UI_URL_PREFIX (
    set "VITE_URL_PREFIX=%UI_URL_PREFIX%"
    echo Building with URL prefix: %UI_URL_PREFIX%
) else (
    set "VITE_URL_PREFIX="
    echo Building for root path
)
call npm run build
if "%errorlevel%" neq "0" (
    echo Failed to build frontend
    exit /B %errorlevel%
)

echo.    
echo Starting backend    
echo.    
cd ..
REM Open browser with correct URL based on UI_URL_PREFIX
if defined UI_URL_PREFIX (
    start http://127.0.0.1:50505%UI_URL_PREFIX%
) else (
    start http://127.0.0.1:50505
)
call python -m quart run --port 50505 --host 127.0.0.1 --reload
if "%errorlevel%" neq "0" (    
    echo Failed to start backend    
    exit /B %errorlevel%    
) 
