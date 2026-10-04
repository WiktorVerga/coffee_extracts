@echo off
REM ============================================================
REM  Reels setup: run it ONCE (and again only to update the tools).
REM  Everything goes inside this folder: .venv\ and .reels\
REM  Nothing is written to C:.
REM ============================================================
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if /i "%~d0"=="C:" (
  echo This folder is on C:. Move the project to another drive first.
  pause & exit /b 1
)

set "R=%~dp0.reels"
for %%D in (tmp appdata\Roaming appdata\Local cache) do if not exist "%R%\%%D" mkdir "%R%\%%D"
set "ORIG_APPDATA=%APPDATA%"
set "ORIG_LOCALAPPDATA=%LOCALAPPDATA%"
set "TEMP=%R%\tmp"
set "TMP=%R%\tmp"
set "APPDATA=%R%\appdata\Roaming"
set "LOCALAPPDATA=%R%\appdata\Local"
set "XDG_CACHE_HOME=%R%\cache"
set "PIP_NO_CACHE_DIR=1"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
set "PYTHONUTF8=1"

if exist ".venv\Scripts\python.exe" goto install

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
  echo Python not found. Install Python 3.12-3.14 and run this again.
  pause & exit /b 1
)
echo Creating the virtual environment in .venv ...
%PY% -m venv .venv || (echo Could not create .venv & pause & exit /b 1)

:install
echo Installing the tools into .venv (about 3 GB, it takes a few minutes) ...
".venv\Scripts\python.exe" -m pip install --no-cache-dir --upgrade pip
".venv\Scripts\python.exe" -m pip install --no-cache-dir --upgrade -r requirements-reels.txt || (echo Installation failed & pause & exit /b 1)

echo.
echo Checking the setup ...
call "%~dp0run-reels.bat" --check --no-pause
pause
