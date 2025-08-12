@echo off
setlocal

:: ==================================================================
::  Streamer's VOD Downloader - Ultimate Robust Launcher
::  - Handles different Python command names (py vs python)
::  - Uses GOTO logic for maximum reliability
:: ==================================================================

:: --- Step 1: Initial Setup ---
cd /d "%~dp0"
set "VENV_DIR=venv"
cls

echo ===========================================
echo  Streamer's VOD Downloader
echo ===========================================
echo.


:: --- Step 2: Check if Environment Exists ---
echo [*] Checking for existing virtual environment...
if exist "%VENV_DIR%\Scripts\python.exe" (
    echo [*] Environment found. Skipping setup.
    goto :LaunchApp
)


:: --- Step 3: Create The Environment (if needed) ---
echo.
echo [!] Environment not found.
echo [*] Starting first-time setup...
echo [*] Searching for a valid Python command (py.exe or python.exe)...

:: Try 'py.exe' first
where py >nul 2>nul
if %errorlevel% equ 0 (
    echo [*] Found 'py.exe'. Using it to create the environment.
    py -3 -m venv "%VENV_DIR%"
    if %errorlevel% neq 0 goto :Error_CreateVenv
    goto :InstallPackages
)

:: If 'py.exe' fails, try 'python.exe'
where python >nul 2>nul
if %errorlevel% equ 0 (
    echo [*] Found 'python.exe'. Using it to create the environment.
    python -m venv "%VENV_DIR%"
    if %errorlevel% neq 0 goto :Error_CreateVenv
    goto :InstallPackages
)

:: If we get here, neither was found.
goto :Error_PythonNotFound


:: --- Step 4: Install Packages (only on first-time setup) ---
:InstallPackages
echo.
echo [*] Environment created successfully.
echo [*] Installing required packages (yt-dlp, ttkthemes)...
echo [*] This may take a moment...
echo.

call "%VENV_DIR%\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check yt-dlp ttkthemes
if %errorlevel% neq 0 goto :Error_Install
echo [*] Packages installed successfully.


:: --- Step 5: Launch The Application ---
:LaunchApp
echo.
echo [*] All checks passed. Launching the application...
call "%VENV_DIR%\Scripts\python.exe" "streamer_downloader.py"
goto :End


:: --- Error Handling Section ---
:Error_PythonNotFound
echo.
echo [!!!] FATAL ERROR: Could not find 'py.exe' OR 'python.exe'.
echo [!!!] Python does not seem to be installed or is not in the system PATH.
echo [!!!] Please install Python from the Microsoft Store or python.org.
echo [!!!] During installation from python.org, MAKE SURE to check the box
echo [!!!] that says "Add Python to PATH".
goto :Error_End

:Error_CreateVenv
echo.
echo [!!!] FATAL ERROR: Found a Python command, but failed to create the environment.
echo [!!!] The installation might be corrupted.
goto :Error_End

:Error_Install
echo.
echo [!!!] FATAL ERROR: Could not install required Python packages.
echo [!!!] Please make sure you are connected to the internet.
goto :Error_End

:Error_End
echo.
pause
exit /b 1


:: --- Clean Exit ---
:End
echo.
echo [*] Application has been closed.
pause

endlocal