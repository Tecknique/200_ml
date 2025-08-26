@echo on
setlocal EnableExtensions

rem === Run from this .bat's folder ===
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%" || (echo [ERROR] Cannot cd to script folder.& pause & exit /b 1)

rem === Settings ===
set "BIN=%SCRIPT_DIR%bin"
set "ENV_PREFIX=%SCRIPT_DIR%env"
set "ENV_YML=%SCRIPT_DIR%environment.yml"
set "CONDA_BAT=%USERPROFILE%\miniforge3\condabin\conda.bat"
set "PORT=8866"
set "URL=http://127.0.0.1:%PORT%/voila/render/app.ipynb"

if not exist "app.ipynb"       (echo [ERROR] Missing app.ipynb & pause & exit /b 1)
if not exist "one_cell_app.py" (echo [ERROR] Missing one_cell_app.py & pause & exit /b 1)
if not exist "%ENV_YML%"       (echo [ERROR] Missing environment.yml & pause & exit /b 1)

if not exist "%BIN%" mkdir "%BIN%"

rem === Install Miniforge if needed (x64). For ARM64, swap URL. ===
if not exist "%CONDA_BAT%" (
  set "MF_EXE=%BIN%\Miniforge3-Windows-x86_64.exe"
  powershell -NoLogo -NoProfile -Command "iwr -UseBasicParsing -Uri 'https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Windows-x86_64.exe' -OutFile '%MF_EXE%'" || (echo [ERROR] Download failed.& pause & exit /b 1)
  start /wait "" "%MF_EXE%" /S /D=%USERPROFILE%\miniforge3 || (echo [ERROR] Miniforge install failed.& pause & exit /b 1)
)

rem === Create or update local env next to the app ===
call "%CONDA_BAT%" env create -p "%ENV_PREFIX%" -f "%ENV_YML%"
if errorlevel 1 call "%CONDA_BAT%" env update -p "%ENV_PREFIX%" -f "%ENV_YML%"
if errorlevel 1 (echo [ERROR] Env solve failed.& pause & exit /b 1)

rem === Launch Voilà (no auth; generic kernel) ===
call "%CONDA_BAT%" run -p "%ENV_PREFIX%" ^
  python -m voila "app.ipynb" ^
  --port=%PORT% --ip=127.0.0.1 ^
  --VoilaConfiguration.kernel_name=python3 ^
  --ServerApp.token= --ServerApp.password= ^
  --ServerApp.open_browser=False ^
  --ServerApp.disable_check_xsrf=True ^
  --debug

echo.
echo If your browser didn't open, paste this:
echo   %URL%
echo.
pause
endlocal

