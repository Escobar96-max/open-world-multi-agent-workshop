@echo off
setlocal enabledelayedexpansion

:: Navigate to script directory
cd /d "%~dp0"

:: Auto-detect Python executable (prioritize virtual environment with pythonw for silent desktop launch)
set "PYTHON_EXE="

if exist "%USERPROFILE%\.venv\Scripts\pythonw.exe" (
    set "PYTHON_EXE=%USERPROFILE%\.venv\Scripts\pythonw.exe"
) else if exist "%~dp0..\.venv\Scripts\pythonw.exe" (
    set "PYTHON_EXE=%~dp0..\.venv\Scripts\pythonw.exe"
) else if exist "%~dp0.venv\Scripts\pythonw.exe" (
    set "PYTHON_EXE=%~dp0.venv\Scripts\pythonw.exe"
) else if exist "%USERPROFILE%\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%USERPROFILE%\.venv\Scripts\python.exe"
) else (
    where pythonw >nul 2>nul
    if !errorlevel! equ 0 (
        set "PYTHON_EXE=pythonw"
    ) else (
        where python >nul 2>nul
        if !errorlevel! equ 0 (
            set "PYTHON_EXE=python"
        )
    )
)

if "%PYTHON_EXE%"=="" (
    echo [ERROR] Python could not be found. Please ensure Python is installed or .venv exists.
    pause
    exit /b 1
)

:: Launch C2 Desktop in a detached process and exit immediately
start "" "%PYTHON_EXE%" run_desktop.py %*
exit /b 0
