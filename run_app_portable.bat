@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion

:: === App paths ===
set "APP_DIR=%~dp0"
cd /d "%APP_DIR%" || (echo [ERROR] Cannot cd to script folder.& pause & exit /b 1)
set "BIN=%APP_DIR%bin"
set "LOG=%APP_DIR%portable-launch.log"
set "ENV_PREFIX=%APP_DIR%env"
set "ENV_YML=%APP_DIR%environment.yml"
set "PORT=8866"
set "URL=http://127.0.0.1:%PORT%/voila/render/app.ipynb"

echo == ONE-CELL portable launcher ==  > "%LOG%"
echo App: %APP_DIR%                      >> "%LOG%"
echo Env: %ENV_PREFIX%                   >> "%LOG%"
echo URL: %URL%                          >> "%LOG%"
echo.

if not exist "app.ipynb"       (echo [ERROR] Missing app.ipynb & goto :fail)
if not exist "one_cell_app.py" (echo [ERROR] Missing one_cell_app.py & goto :fail)
if not exist "%ENV_YML%"       (echo [ERROR] Missing environment.yml & goto :fail)

if not exist "%BIN%" mkdir "%BIN%" >nul 2>&1

:: === Find or install Miniforge (user folder, no admin) ===
set "CONDA_BAT=%USERPROFILE%\miniforge3\condabin\conda.bat"
if not exist "%CONDA_BAT%" (
  echo Miniforge not found. Installing to %USERPROFILE%\miniforge3 ...
  set "MF_EXE=%BIN%\Miniforge3-Windows-x86_64.exe"
  powershell -NoLogo -NoProfile -Command "try { iwr -UseBasicParsing -Uri 'https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Windows-x86_64.exe' -OutFile '%MF_EXE%'; exit 0 } catch { Write-Host $_; exit 1 }" >> "%LOG%" 2>&1
  if not exist "%MF_EXE%" (echo [ERROR] Download failed. See %LOG%. & goto :fail)
  start /wait "" "%MF_EXE%" /S /D=%USERPROFILE%\miniforge3
)
if not exist "%CONDA_BAT%" (echo [ERROR] Miniforge install failed. See %LOG%. & goto :fail)

echo Using: "%CONDA_BAT%"

:: === Create / update a local env by prefix (lives inside the app folder) ===
echo Creating/updating environment (first run can take a while)...
call "%CONDA_BAT%" env create -p "%ENV_PREFIX%" -f "%ENV_YML%" >> "%LOG%" 2>&1
if errorlevel 1 (
  call "%CONDA_BAT%" env update -p "%ENV_PREFIX%" -f "%ENV_YML%" >> "%LOG%" 2>&1
  if errorlevel 1 (echo [ERROR] Env solve failed. See %LOG%. & goto :fail)
)

:: === Launch Voilà (no auth; generic kernel) ===
echo Starting Voilà...
start "ONE-CELL Portable (Voila)" /b cmd /c ^
  call "%CONDA_BAT%" run -p "%ENV_PREFIX%" ^
    python -m voila "app.ipynb" ^
    --port=%PORT% --ip=127.0.0.1 ^
    --VoilaConfiguration.kernel_name=python3 ^
    --ServerApp.token='' --ServerApp.password='' ^
    --ServerApp.open_browser=False ^
    --ServerApp.disable_check_xsrf=True ^
    --debug >> "%LOG%" 2>&1

:: === Probe and open the browser when ready ===
for /l %%i in (1,1,120) do (
  powershell -NoLogo -NoProfile -Command "try { iwr -UseBasicParsing -Method Head -Uri '%URL%' | Out-Null; exit 0 } catch { Start-Sleep -Milliseconds 0; exit 1 }"
  if not errorlevel 1 (start "" "%URL%" & goto :ok)
  timeout /t 1 >nul
)

echo [WARN] Server didn’t confirm in time; opening anyway...
start "" "%URL%"

:ok
echo.
echo [OK] Running at:
echo   %URL%
echo If the page doesn’t load, open this log:
echo   %LOG%
echo Press any key to close this window (server keeps running)...
pause >nul
exit /b 0

:fail
echo.
echo [FAILED] See the last lines of the log:
powershell -NoLogo -NoProfile -Command "if (Test-Path '%LOG%') { Get-Content -Path '%LOG%' -Tail 60 }"
echo.
echo Full log: %LOG%
echo Press any key to close...
pause >nul
exit /b 1
