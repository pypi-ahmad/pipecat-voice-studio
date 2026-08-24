@echo off
setlocal

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch.ps1" %*
set "PVS_EXIT_CODE=%ERRORLEVEL%"

if not "%PVS_EXIT_CODE%"=="0" (
    echo.
    echo Pipecat Voice Studio failed to launch. Exit code: %PVS_EXIT_CODE%
    pause
)

exit /b %PVS_EXIT_CODE%
