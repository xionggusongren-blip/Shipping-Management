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

REM --- Windows Firewall: ポート8443を自動開放 ---
echo [INFO] ファイアウォール設定を確認中...
netsh advfirewall firewall show rule name="ShippingMgmt-8443" >nul 2>&1
if errorlevel 1 (
    echo [INFO] ファイアウォールにポート8443のルールを追加中...
    netsh advfirewall firewall add rule name="ShippingMgmt-8443" protocol=TCP dir=in localport=8443 action=allow >nul 2>&1
    if errorlevel 1 (
        echo [WARNING] ファイアウォール設定に失敗しました（管理者権限が必要な場合があります）
        echo           右クリック→「管理者として実行」で start.bat を再実行してください
    ) else (
        echo [INFO] ファイアウォール: ポート8443を開放しました
    )
) else (
    echo [INFO] ファイアウォール: ポート8443はすでに開放済みです
)

REM --- PCのIPアドレスを取得（192.168.x.x を優先）---
set PC_IP=
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /R "IPv4"') do (
    set CANDIDATE=%%a
    set CANDIDATE=!CANDIDATE: =!
    echo !CANDIDATE! | findstr /b "192.168." >nul 2>&1
    if not errorlevel 1 set PC_IP=!CANDIDATE!
)
REM 192.168.x.x がなければ最初のIPを使用
if "%PC_IP%"=="" (
    for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /R "IPv4"') do (
        if "%PC_IP%"=="" (
            set PC_IP=%%a
            set PC_IP=!PC_IP: =!
        )
    )
)

REM --- SSL証明書を毎回再生成（IPアドレス変化に対応） ---
echo [INFO] SSL証明書を生成中...
cd backend
if exist cert.pem del cert.pem
if exist key.pem del key.pem
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
echo   起動完了！スマホからアクセス
echo ======================================
echo.
echo   1. スマホとPCが同じWiFiに接続されているか確認
echo.
echo   2. スマホのブラウザで以下のURLを開く:
echo      https://%PC_IP%:8443
echo.
echo   3. 「接続がプライベートではありません」という
echo      警告が出たら:
echo      [Chrome] 詳細設定 → %PC_IP% にアクセスする
echo      [Safari] 詳細を表示 → このWebサイトを閲覧
echo.
echo   ※ PC から確認: https://localhost:8443
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
