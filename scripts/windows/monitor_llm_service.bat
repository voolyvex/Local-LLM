@echo off
setlocal enabledelayedexpansion

set "PROJECT_ROOT=%~dp0..\..\"
set "LOG_FILE=%PROJECT_ROOT%\logs\shadow-worker\service_monitor.log"

:: Create logs directory if it doesn't exist
if not exist "%PROJECT_ROOT%\logs\shadow-worker" (
    mkdir "%PROJECT_ROOT%\logs\shadow-worker"
)

:: Function to check if service is running
:check_service
echo [%date% %time%] Checking LLM service status... >> "%LOG_FILE%"

:: Check if the service is running on port 8002
netstat -ano | findstr ":8002" > nul
if %ERRORLEVEL% equ 0 (
    echo [%date% %time%] LLM service is running on port 8002 >> "%LOG_FILE%"
) else (
    echo [%date% %time%] LLM service is not running, attempting to start... >> "%LOG_FILE%"
    call :start_service
)

goto :sleep

:start_service
echo [%date% %time%] Starting LLM service... >> "%LOG_FILE%"
start /B cmd /c "cd /D "%PROJECT_ROOT%" && python src\api\server.py >> "%LOG_FILE%" 2>&1"

:: Wait for service to start
timeout /t 10 /nobreak > nul
echo [%date% %time%] Service start attempt completed >> "%LOG_FILE%"
exit /b 0

:sleep
:: Wait before checking again
timeout /t 60 /nobreak > nul
goto :check_service 