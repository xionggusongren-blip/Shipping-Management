@echo off
setlocal enabledelayedexpansion
chcp 65001 > nul

echo ======================================
echo   荷物管理Webアプリ 起動
echo ======================================
echo.

REM スクリプトのあるフォルダをカレントに設定
cd /d "%~dp0"

REM ---------- セットアップ確認 ----------
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

REM ---------- 仮想環境の有効化 ----------
call .venv\Scripts\activate.bat

REM ---------- 依存関係確認 ----------
echo [INFO] 依存関係を確認中...
pip install --quiet -r backend\requirements.txt
if errorlevel 1 (
    echo [ERROR] pip install に失敗しました
    pause
    exit /b 1
)
echo [INFO] IBM i 接続ライブラリを確認中（失敗しても動作可）...
pip install --quiet -r backend\requirements-ibmi.txt 2>nul || echo [WARNING] IBM i ライブラリ未インストール（DEMO_MODE で動作します）

REM ---------- SSL証明書の生成 ----------
echo [INFO] SSL証明書を確認中...
cd backend
python generate_cert.py
if errorlevel 1 (
    echo [WARNING] SSL証明書の生成に失敗しました。HTTPで起動します。
    cd ..
    goto :start_http
)
cd ..

REM ---------- アプリ起動 (HTTPS) ----------
:start_https
echo.
echo ======================================
echo   アクセスURL
echo ======================================
echo   PC:     https://localhost:8443
echo   スマホ: https://(PCのIPアドレス):8443
echo   ※ 初回アクセス時にブラウザの警告が出ます
echo     「詳細設定」→「安全でないサイトへ進む」を選択してください
echo ======================================
echo   停止するには Ctrl+C を押してください
echo.

cd backend
uvicorn main:app --host 0.0.0.0 --port 8443 --ssl-keyfile key.pem --ssl-certfile cert.pem --reload
goto :end

REM ---------- アプリ起動 (HTTP フォールバック) ----------
:start_http
echo [INFO] http://localhost:8000 でアプリを起動します（カメラ機能は使用できません）
echo        停止するには Ctrl+C を押してください
echo.

cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

:end

pause
