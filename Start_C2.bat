@echo off
setlocal enabledelayedexpansion

:: Navigate to script directory
cd /d "%~dp0"

:: Auto-detect Python executable (prioritize virtual environment with python for visual feedback)
set "PYTHON_EXE="

if exist "%USERPROFILE%\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%USERPROFILE%\.venv\Scripts\python.exe"
) else if exist "%USERPROFILE%\.venv\Scripts\pythonw.exe" (
    set "PYTHON_EXE=%USERPROFILE%\.venv\Scripts\pythonw.exe"
) else if exist "%~dp0..\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0..\.venv\Scripts\python.exe"
) else if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
) else (
    where python >nul 2>nul
    if !errorlevel! equ 0 (
        set "PYTHON_EXE=python"
    ) else (
        where pythonw >nul 2>nul
        if !errorlevel! equ 0 (
            set "PYTHON_EXE=pythonw"
        )
    )
)

if "%PYTHON_EXE%"=="" (
    echo [ERROR] Python could not be found. Please ensure Python is installed or .venv exists.
    pause
    exit /b 1
)

:: Launch C2 Desktop with error trapping and diagnostics
echo ===================================================================
echo   Starting Antigravity Unified C2 Desktop Executive System...
echo   Python: %PYTHON_EXE%
echo ===================================================================

"%PYTHON_EXE%" "%~dp0run_desktop.py" %*
if !errorlevel! neq 0 (
    echo.
    echo ===================================================================
    echo [ERROR] Antigravity C2 Desktop exited with code !errorlevel!.
    echo Check launcher.log for details, or install missing dependencies:
    echo   "%PYTHON_EXE%" -m pip install -r "%~dp0requirements.txt"
    echo ===================================================================
    pause
    exit /b !errorlevel!
)
exit /b 0
