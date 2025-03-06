@echo off
setlocal enabledelayedexpansion

:: Set up environment
set "PROJECT_ROOT=%~dp0..\..\"
cd /D "%PROJECT_ROOT%"

echo Current directory: %CD%
if not exist "src\api\server.py" (
    echo Error: Not in Local-LLM project root
    exit /b 1
)

:: Create required directories
if not exist "logs\shadow-worker" mkdir "logs\shadow-worker"
if not exist "data\shadow-worker" mkdir "data\shadow-worker"

:: Parse arguments
set "USE_GPU=true"
set "MODEL_SIZE=medium"
set "DEBUG=false"

:parse_args
if "%~1"=="" goto :end_parse_args
if /i "%~1"=="--cpu-only" set "USE_GPU=false"
if /i "%~1"=="--model-size" (
    if /i "%~2"=="small" set "MODEL_SIZE=small"
    if /i "%~2"=="medium" set "MODEL_SIZE=medium"
    if /i "%~2"=="large" set "MODEL_SIZE=large"
    shift
)
if /i "%~1"=="--debug" set "DEBUG=true"
shift
goto :parse_args
:end_parse_args

:: Configure GPU layers based on model size
set "GPU_LAYERS=0"
if "%USE_GPU%"=="true" (
    if "%MODEL_SIZE%"=="small" set "GPU_LAYERS=20"
    if "%MODEL_SIZE%"=="medium" set "GPU_LAYERS=35" 
    if "%MODEL_SIZE%"=="large" set "GPU_LAYERS=60"
)

:: Set environmental variables
set "PYTHON_PATH=.;src"
set "SW_CONFIG_PATH=config/shadow-worker/config.py"
set "SW_GPU_LAYERS=%GPU_LAYERS%"

echo.
echo Shadow Worker LLM Service
echo ------------------------------------------
echo Model Size: %MODEL_SIZE%
echo GPU Layers: %GPU_LAYERS%
echo Debug Mode: %DEBUG%
echo ------------------------------------------
echo.

:: Start the service
if "%DEBUG%"=="true" (
    python src\api\server.py --config "%SW_CONFIG_PATH%" --gpu-layers %GPU_LAYERS% --verbose
) else (
    start "Shadow Worker LLM" /B python src\api\server.py --config "%SW_CONFIG_PATH%" --gpu-layers %GPU_LAYERS%
    echo Service started in background mode. Monitor logs at logs\shadow-worker\
)

:: Start monitoring if not in debug mode
if "%DEBUG%"=="false" (
    start "LLM Monitor" /B scripts\windows\monitor_llm_service.bat
    echo Service monitoring started
)

exit /b 0 