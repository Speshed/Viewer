@echo off
setlocal EnableExtensions

set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

pushd "%PROJECT_DIR%" >nul || (
    echo [ERROR] Failed to open project folder: "%PROJECT_DIR%"
    exit /b 1
)

set "EXPORT_VIEWER_SCRIPT=%PROJECT_DIR%\export_viewer_main.py"
set "EXPORT_VIEWER_NAME=Larix_Export_Viewer"
set "ICON_FILE=%PROJECT_DIR%\icon\logo.ico"
set "DIST_DIR=%PROJECT_DIR%\dist"
set "BUILD_DIR=%PROJECT_DIR%\build"
set "SPEC_DIR=%PROJECT_DIR%"

if not exist "%EXPORT_VIEWER_SCRIPT%" (
    echo [ERROR] Entry script not found: "%EXPORT_VIEWER_SCRIPT%"
    popd >nul
    exit /b 1
)

where py >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Command "py" was not found. Install Python Launcher for Windows.
    popd >nul
    exit /b 1
)

py -3 -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PyInstaller is not installed in the selected Python.
    echo Install it with: py -3 -m pip install pyinstaller
    popd >nul
    exit /b 1
)

for %%P in (PySide6 pandas requests openpyxl pyodbc tenacity) do (
    py -3 -c "import %%P" >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Missing package: %%P
        echo Install project dependencies and run the build again.
        popd >nul
        exit /b 1
    )
)

set "PYARROW_ARGS="
py -3 -c "import pyarrow" >nul 2>&1
if not errorlevel 1 (
    set "PYARROW_ARGS=--collect-binaries pyarrow --collect-data pyarrow --hidden-import pyarrow --hidden-import pyarrow.lib --hidden-import pyarrow.compute --hidden-import pyarrow._compute --hidden-import pyarrow.parquet --hidden-import pyarrow._parquet --hidden-import pyarrow.dataset --hidden-import pyarrow._dataset --hidden-import pyarrow._dataset_parquet --hidden-import pyarrow.fs --hidden-import pyarrow._fs --hidden-import pyarrow.pandas_compat"
)
if errorlevel 1 (
    echo [WARN] pyarrow was not found.
    echo [WARN] The built EXE will work, but Parquet export in BIM Sync mode will be unavailable.
)

set "COMMON_ARGS=--noconfirm --clean --onefile --windowed --distpath "%DIST_DIR%" --specpath "%SPEC_DIR%" --paths "%PROJECT_DIR%\Viewer" --paths "%PROJECT_DIR%\Sync" --paths "%PROJECT_DIR%\shared" --add-data "%PROJECT_DIR%\Viewer;Viewer" --add-data "%PROJECT_DIR%\Sync;Sync" --add-data "%PROJECT_DIR%\shared;shared" --add-data "%PROJECT_DIR%\icon;icon" --hidden-import pyodbc --hidden-import tenacity --hidden-import pandas --hidden-import requests --hidden-import openpyxl --collect-binaries pyodbc --collect-data certifi %PYARROW_ARGS%"

rem --- Clean previous builds ---
if exist "%DIST_DIR%\%EXPORT_VIEWER_NAME%.exe" del /f /q "%DIST_DIR%\%EXPORT_VIEWER_NAME%.exe" >nul 2>&1
if exist "%BUILD_DIR%\export_viewer" rmdir /s /q "%BUILD_DIR%\export_viewer" >nul 2>&1
if exist "%SPEC_DIR%\%EXPORT_VIEWER_NAME%.spec" del /f /q "%SPEC_DIR%\%EXPORT_VIEWER_NAME%.spec" >nul 2>&1

rem =============================================
echo [INFO] Building %EXPORT_VIEWER_NAME%...
echo =============================================
py -3 -m PyInstaller %COMMON_ARGS% --workpath "%BUILD_DIR%\export_viewer" --name "%EXPORT_VIEWER_NAME%" --icon "%ICON_FILE%" "%EXPORT_VIEWER_SCRIPT%"
if errorlevel 1 (
    echo [ERROR] %EXPORT_VIEWER_NAME% build failed.
    popd >nul
    exit /b 1
)
echo [OK] %EXPORT_VIEWER_NAME% done: "%DIST_DIR%\%EXPORT_VIEWER_NAME%.exe"

echo.
echo =============================================
echo [DONE] Build completed:
echo   "%DIST_DIR%\%EXPORT_VIEWER_NAME%.exe"
echo =============================================

popd >nul
exit /b 0
