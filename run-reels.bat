@echo off
REM ============================================================
REM  Prepares the reels from the "Idee Reel" sheet and pushes them to GitHub.
REM  Double-click it after adding rows to the sheet.
REM  Options: --dry-run  --only 3  --retry  --check
REM  Nothing is written to C: (temp, caches and models stay in .reels\).
REM ============================================================
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "NOPAUSE="
set "ARGS="
:args
if "%~1"=="" goto argsdone
if /i "%~1"=="--no-pause" (set "NOPAUSE=1") else (set "ARGS=%ARGS% %1")
shift
goto args
:argsdone

if not exist ".venv\Scripts\python.exe" (
  echo Environment not found: run setup-reels.bat first.
  if not defined NOPAUSE pause
  exit /b 1
)

set "R=%~dp0.reels"
for %%D in (tmp appdata\Roaming appdata\Local cache) do if not exist "%R%\%%D" mkdir "%R%\%%D"
REM git needs the real folders (saved credentials): the script restores them for git only
if not defined ORIG_APPDATA set "ORIG_APPDATA=%APPDATA%"
if not defined ORIG_LOCALAPPDATA set "ORIG_LOCALAPPDATA=%LOCALAPPDATA%"
set "TEMP=%R%\tmp"
set "TMP=%R%\tmp"
set "APPDATA=%R%\appdata\Roaming"
set "LOCALAPPDATA=%R%\appdata\Local"
set "XDG_CACHE_HOME=%R%\cache"
set "PIP_NO_CACHE_DIR=1"
set "PYTHONUTF8=1"
set "PATH=%~dp0.venv\Scripts;%PATH%"

".venv\Scripts\python.exe" scripts\prepare_reels.py %ARGS%
set "CODE=%ERRORLEVEL%"
echo.
if not defined NOPAUSE pause
exit /b %CODE%
