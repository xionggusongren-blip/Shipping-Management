@echo off
chcp 65001 > nul

cd /d "%~dp0"

REM -------------------------------------------------------
REM  Safe self-update: fetch new code, then restart once
REM -------------------------------------------------------
if "%_UPDATED%"=="" (
    echo [INFO] Fetching latest code...
    git fetch origin 2>nul
    git checkout claude/create-from-requirements-bqqkU 2>nul
    git pull origin claude/create-from-requirements-bqqkU 2>nul
    set _UPDATED=1
    cmd /c "%~f0"
    exit /b
)

setlocal enabledelayedexpansion

echo ======================================
echo   荷物管理Webアプリ 起動
echo ======================================
echo.

REM --- Setup check ---
if not exist ".venv" (
    echo [ERROR] 仮想環境が見つかりません。先に install.bat を実行してください。
    pause
    exit /b 1
)

if not exist "backend\.env" (
    echo [WARNING] backend\.env が見つかりません。.env.example からコピーします...
    copy "backend\.env.example" "backend\.env" > nul
    echo.
    echo  backend\.env を開いて IBM i 接続情報を設定してから再度実行してください。
    echo  ※ DEMO_MODE=true のままでもサンプルデータで動作確認できます。
    pause
    exit /b 1
)

REM --- Activate venv ---
call .venv\Scripts\activate.bat

REM --- Install dependencies ---
echo [INFO] 依存関係を確認中...
pip install --quiet -r backend\requirements.txt
if errorlevel 1 (
    echo [ERROR] pip install に失敗しました
    pause
    exit /b 1
)
echo [INFO] IBM i 接続ライブラリを確認中（失敗しても動作可）...
pip install --quiet -r backend\requirements-ibmi.txt 2>nul
python -c "import pyodbc; print('[OK] pyodbc', pyodbc.version)" 2>nul || echo [WARNING] pyodbc 未インストール - pip install pyodbc を実行してください

REM --- Generate SSL cert ---
echo [INFO] SSL cert generating...
cd backend
python generate_cert.py
if errorlevel 1 (
    echo [WARNING] SSL cert failed. Starting HTTP mode.
    cd ..
    goto :start_http
)
cd ..

REM --- Start app (HTTPS) ---
:start_https
echo.
echo ======================================
echo   Access URL
echo ======================================
echo   PC    : https://localhost:8443
echo   PHONE : https://192.168.0.136:8443
echo   NOTE  : Accept browser security warning on first access
echo           Safari: [詳細を表示] then [このWebサイトを閲覧]
echo           Chrome: [詳細設定] then [アクセスする]
echo ======================================
echo   Press Ctrl+C to stop
echo.

cd backend
uvicorn main:app --host 0.0.0.0 --port 8443 --ssl-keyfile key.pem --ssl-certfile cert.pem --reload
goto :end

REM --- Start app (HTTP fallback) ---
:start_http
echo [INFO] Starting HTTP mode on port 8000 (camera unavailable)
echo        Press Ctrl+C to stop
echo.

cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

:end
pause
