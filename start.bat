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
REM SSL証明書生成に必要
pip install --quiet cryptography 2>nul
echo [INFO] IBM i 接続ライブラリを確認中（失敗しても動作可）...
pip install --quiet -r backend\requirements-ibmi.txt 2>nul
python -c "import pyodbc; print('[OK] pyodbc', pyodbc.version)" 2>nul || echo [WARNING] pyodbc 未インストール

REM --- Generate SSL cert (再生成が必要な場合は cert.pem / key.pem を削除) ---
echo [INFO] SSL証明書を確認中...
cd backend
python generate_cert.py
if errorlevel 1 (
    echo [WARNING] SSL証明書の生成に失敗しました。HTTPモードで起動します
    echo [WARNING] スマホからのQRスキャンは HTTPS が必要です
    cd ..
    goto :start_http
)
cd ..

REM --- Start app (HTTPS) ---
:start_https
echo.
echo ======================================
echo   起動完了 - アクセスURL
echo ======================================
echo   PC    : https://localhost:8443
echo   スマホ: 上記の generate_cert.py の出力を確認
echo.
echo   ※ 初回は証明書警告が出ます
echo      Chrome: 詳細設定 → アクセスする
echo      Safari: 詳細を表示 → このWebサイトを閲覧
echo.
echo   ファイアウォールでポート 8443 を開放してください
echo   [Windowsの場合]
echo   netsh advfirewall firewall add rule name="ShippingMgmt" ^
echo     protocol=TCP dir=in localport=8443 action=allow
echo ======================================
echo   Ctrl+C で停止
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
