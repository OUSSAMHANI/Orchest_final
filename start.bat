@echo off
title Orchestrator Launcher
echo ========================================
echo   Multi-Agent Orchestrator
echo ========================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.11+
    pause
    exit /b 1
)

REM Create virtual environment if not exists
if not exist venv (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    echo [INFO] Virtual environment created.
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate

REM Upgrade pip
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip -q

REM Install dependencies
if exist requirements.txt (
    echo [INFO] Installing dependencies...
    pip install -r requirements.txt -q
) else (
    echo [WARNING] requirements.txt not found
)

REM Create .env file if not exists
if not exist .env (
    if exist .env.example (
        echo [INFO] Creating .env from .env.example...
        copy .env.example .env >nul
        echo [WARNING] Please edit .env with your API keys
    ) else (
        echo [WARNING] .env.example not found
    )
)

REM Create workspace directory
if not exist workspace (
    echo [INFO] Creating workspace directory...
    mkdir workspace
)

REM Create logs directory
if not exist logs (
    echo [INFO] Creating logs directory...
    mkdir logs
)

echo.
echo ========================================
echo   Starting Orchestrator...
echo ========================================
echo.
echo   API: http://localhost:8000
echo   Docs: http://localhost:8000/docs
echo   Health: http://localhost:8000/health
echo.
echo   Press CTRL+C to stop
echo ========================================
echo.

REM Start the orchestrator
uvicorn orchestrator.main:app --reload --host 0.0.0.0 --port 8000

pause