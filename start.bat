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

REM ---------- アプリ起動 ----------
echo [INFO] http://localhost:8000 でアプリを起動します
echo        ブラウザで上記 URL を開いてください
echo        停止するには Ctrl+C を押してください
echo.

cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause
