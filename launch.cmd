@echo off
rem Windows CMD trampoline script forwarding invocation and arguments to launch.ps1.
rem Does not execute application logic directly. Next file to open: launch.ps1.
setlocal


powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch.ps1" %*
set "PVS_EXIT_CODE=%ERRORLEVEL%"

if not "%PVS_EXIT_CODE%"=="0" (
    echo.
    echo Pipecat Voice Studio failed to launch. Exit code: %PVS_EXIT_CODE%
    pause
)

exit /b %PVS_EXIT_CODE%
