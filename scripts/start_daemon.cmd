@echo off
chcp 65001 >nul
setlocal
set "BASE=%~dp0"
echo [plc_mcp] 正在给已运行的 InoProShop 注入守护（UIA 触发，不动鼠标、不抢焦点）...
powershell -NoProfile -ExecutionPolicy Bypass -File "%BASE%ide_trigger.ps1" -ScriptPath "%BASE%ide\plc_daemon.py" -TimeoutSec 60
echo.
if exist "%BASE%ipc\ready.flag" (
  echo [OK] 守护已就绪，bridge 可以直接调用了
) else (
  echo [FAIL] 未就绪，查看 %BASE%ipc\daemon_boot.log 排错
)
echo.
pause
