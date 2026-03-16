@echo off
setlocal enabledelayedexpansion
chcp 65001 > nul

echo ======================================
echo   jt400.jar ダウンロード
echo   (IBM JTOpen - Apache License 2.0)
echo ======================================
echo.

REM ダウンロード先
set DEST_DIR=C:\jt400
set DEST_FILE=%DEST_DIR%\jt400.jar
set VERSION=20.0.7
set URL=https://repo1.maven.org/maven2/net/sf/jt400/jt400/%VERSION%/jt400-%VERSION%.jar

REM すでに存在する場合はスキップ
if exist "%DEST_FILE%" (
    echo [OK] %DEST_FILE% はすでに存在します。スキップします。
    goto :update_env
)

REM ダウンロード先フォルダ作成
if not exist "%DEST_DIR%" (
    echo [INFO] フォルダを作成: %DEST_DIR%
    mkdir "%DEST_DIR%"
)

echo [INFO] jt400.jar v%VERSION% をダウンロード中...
echo        取得元: %URL%
echo        保存先: %DEST_FILE%
echo.

powershell -NoProfile -Command "Invoke-WebRequest -Uri '%URL%' -OutFile '%DEST_FILE%' -UseBasicParsing"
if errorlevel 1 (
    echo.
    echo [ERROR] ダウンロードに失敗しました。
    echo         ネットワーク接続とプロキシ設定を確認してください。
    echo         手動でダウンロードする場合:
    echo           %URL%
    echo         上記URLをブラウザで開き、%DEST_FILE% に保存してください。
    pause
    exit /b 1
)

echo [OK] ダウンロード完了: %DEST_FILE%

:update_env
REM backend\.env の IBMI_DRIVER_PATH を更新
if not exist "backend\.env" (
    echo [WARNING] backend\.env が見つかりません。先に install.bat を実行してください。
    goto :end
)

echo.
echo [INFO] backend\.env の IBMI_DRIVER_PATH を更新中...

REM 既存の行を書き換え（PowerShell で処理）
powershell -NoProfile -Command ^
    "(Get-Content 'backend\.env') -replace '^IBMI_DRIVER_PATH=.*', 'IBMI_DRIVER_PATH=%DEST_FILE%' | Set-Content 'backend\.env'"

echo [OK] backend\.env を更新しました: IBMI_DRIVER_PATH=%DEST_FILE%

:end
echo.
echo ======================================
echo   完了！
echo   次は backend\.env に IBMI_USER と
echo   IBMI_PASSWORD を設定してください。
echo ======================================
pause
