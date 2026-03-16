@echo off
setlocal enabledelayedexpansion
chcp 65001 > nul

echo ======================================
echo   荷物管理Webアプリ セットアップ
echo ======================================
echo.

REM スクリプトのあるフォルダをカレントに設定
cd /d "%~dp0"

REM ---------- Python 確認 ----------
python --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python が見つかりません。
    echo         https://www.python.org/ から Python 3.11 以上をインストールし、
    echo         "Add Python to PATH" にチェックを入れて再インストールしてください。
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] Python %PYVER% を検出しました

REM ---------- 仮想環境 ----------
if not exist ".venv" (
    echo [INFO] 仮想環境を作成中...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] 仮想環境の作成に失敗しました
        pause
        exit /b 1
    )
)
echo [OK] 仮想環境: .venv

REM ---------- 依存関係インストール ----------
echo [INFO] 依存関係をインストール中（時間がかかる場合があります）...
call .venv\Scripts\activate.bat
pip install --quiet -r backend\requirements.txt
if errorlevel 1 (
    echo [ERROR] pip install に失敗しました
    pause
    exit /b 1
)
echo [OK] 依存関係インストール完了

REM ---------- .env 作成 ----------
if not exist "backend\.env" (
    copy "backend\.env.example" "backend\.env" > nul
    echo [INFO] backend\.env を作成しました
    echo.
    echo ============================================================
    echo  backend\.env を開いて以下を設定してください:
    echo    IBMI_HOST      : IBM i の IP アドレス（192.168.3.230）
    echo    IBMI_USER      : IBM i ユーザー名
    echo    IBMI_PASSWORD  : IBM i パスワード
    echo    IBMI_DRIVER_PATH: jt400.jar のフルパス
    echo    DEMO_MODE      : テスト時は true、本番は false
    echo ============================================================
) else (
    echo [OK] backend\.env は既に存在します
)

echo.
echo ======================================
echo   セットアップ完了！
echo   start.bat でアプリを起動してください
echo ======================================
pause
