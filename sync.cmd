@echo off
chcp 65001 >nul
REM sync.cmd - one-click sync wrapper
REM Bypasses PowerShell execution policy (many machines block .ps1 by default).
REM
REM Usage:
REM   sync.cmd
REM   sync.cmd "fix: correct IN pin type note"
REM   sync.cmd -DryRun
REM   sync.cmd -AllowEmptyChangelog
REM
REM Also works in Git Bash: ./sync.cmd "message"

setlocal
set "SCRIPT_DIR=%~dp0"
set "PS1=%SCRIPT_DIR%sync.ps1"

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%" %*

set "RC=%ERRORLEVEL%"
endlocal & exit /b %RC%
