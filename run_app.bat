@echo off
chcp 65001 >nul
setlocal EnableExtensions

rem === Use Miniforge's conda so it sees your onecell env ===
set "CONDA_BAT=%USERPROFILE%\miniforge3\condabin\conda.bat"
set "ENV=onecell"
set "PORT=8866"
set "URL=http://127.0.0.1:%PORT%/voila/render/app.ipynb"

cd /d "%~dp0" || (echo [ERROR] Cannot cd to script folder.& pause & exit /b 1)

if not exist "app.ipynb"        (echo [ERROR] Missing app.ipynb in %cd% & pause & exit /b 1)
if not exist "one_cell_app.py"  (echo [ERROR] Missing one_cell_app.py in %cd% & pause & exit /b 1)
if not exist "%CONDA_BAT%"      (echo [ERROR] Miniforge conda.bat not found at: %CONDA_BAT% & pause & exit /b 1)

echo Using: "%CONDA_BAT%"
echo Env:    %ENV%
echo Port:   %PORT%
echo URL:    %URL%
echo.

rem Foreground so you can see errors; kernel forced; auth disabled
call "%CONDA_BAT%" run -n %ENV% ^
  python -m voila "app.ipynb" ^
  --port=%PORT% --ip=127.0.0.1 ^
  --VoilaConfiguration.kernel_name=%ENV% ^
  --ServerApp.token='' --ServerApp.password='' ^
  --ServerApp.open_browser=False ^
  --ServerApp.disable_check_xsrf=True ^
  --debug

echo.
echo If the page didn't open, paste this in your browser:
echo   %URL%
echo.
pause
endlocal
