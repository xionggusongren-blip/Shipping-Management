@echo off
chcp 65001 > nul
cd /d "%~dp0"

REM -------------------------------------------------------
REM  ファイアウォール設定スクリプト
REM  ポート 8443 を開放します（初回のみ実行してください）
REM -------------------------------------------------------

REM --- 管理者権限チェック・自動昇格 ---
net session >nul 2>&1
if errorlevel 1 (
    echo [INFO] 管理者権限が必要です。UAC プロンプトを表示します...
    powershell -Command "Start-Process cmd -ArgumentList '/c cd /d \"%~dp0\" && \"%~f0\"' -Verb RunAs -Wait"
    exit /b
)

echo ======================================
echo   ファイアウォール設定
echo ======================================
echo.

REM --- 既存ルール削除 ---
netsh advfirewall firewall delete rule name="ShippingMgmt-8443" >nul 2>&1

REM --- 新規ルール追加 ---
netsh advfirewall firewall add rule ^
    name="ShippingMgmt-8443" ^
    protocol=TCP ^
    dir=in ^
    localport=8443 ^
    action=allow ^
    description="荷物管理Webアプリ HTTPS ポート"

if errorlevel 1 (
    echo [ERROR] ファイアウォール設定に失敗しました
    pause
    exit /b 1
)

echo.
echo [OK] ポート 8443 を開放しました
echo      スマホから https://[PCのIP]:8443 でアクセスできます
echo.
echo このウィンドウは閉じて構いません。
echo start.bat を実行してアプリを起動してください。
echo.
pause
