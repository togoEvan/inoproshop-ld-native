@echo off
chcp 65001 >nul
setlocal
rem bridge.cmd —— 命令行调用入口，自动挑一个真能跑的 Python 3
rem 用法:  bridge.cmd ping
rem        bridge.cmd eval_file D:\plc_mcp\ide\tasks\task_check.py
rem 可用 PLC_PYTHON 指定解释器（Windows 应用商店的 python.exe 是 0 字节存根，不能用）

if defined PLC_PYTHON (
  if exist "%PLC_PYTHON%" (
    "%PLC_PYTHON%" "%~dp0bridge.py" %*
    exit /b %ERRORLEVEL%
  )
)

where py >nul 2>nul
if not errorlevel 1 (
  py -3 -c "import sys" >nul 2>nul
  if not errorlevel 1 (
    py -3 "%~dp0bridge.py" %*
    exit /b %ERRORLEVEL%
  )
)

where python >nul 2>nul
if not errorlevel 1 (
  python -c "import sys; sys.exit(0 if sys.version_info[0]==3 else 1)" >nul 2>nul
  if not errorlevel 1 (
    python "%~dp0bridge.py" %*
    exit /b %ERRORLEVEL%
  )
)

echo [plc_mcp] 未找到可用的 Python 3。
echo   装一个 Python 3，或设置环境变量 PLC_PYTHON=完整路径\python.exe
exit /b 1
