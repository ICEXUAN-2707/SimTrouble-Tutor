@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Python environment is missing. Follow the first-time setup in README.md.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -B "tools\start_product.py" %*
set "launcher_exit=%errorlevel%"
if not "%launcher_exit%"=="0" (
  echo.
  echo Product startup stopped. Review the message above.
  pause
)
exit /b %launcher_exit%
