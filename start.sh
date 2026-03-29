#!/bin/bash
# 荷物管理Webアプリ 起動スクリプト

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"

echo "======================================"
echo "  荷物管理Webアプリ 起動"
echo "======================================"

# .env ファイルの確認
if [ ! -f "$BACKEND_DIR/.env" ]; then
    echo "[INFO] .env が見つかりません。.env.example からコピーします..."
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
    echo "[WARNING] $BACKEND_DIR/.env を編集してIBM i 接続情報を設定してください"
fi

# Python 仮想環境
VENV_DIR="$SCRIPT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "[INFO] 仮想環境を作成中..."
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

echo "[INFO] 依存関係をインストール中..."
pip install -q -r "$BACKEND_DIR/requirements.txt"

# SSL証明書の生成（スマホカメラ使用に必要）
cd "$BACKEND_DIR"
echo "[INFO] SSL証明書を確認中..."
python3 generate_cert.py || true

# HTTPS or HTTP フォールバック
if [ -f "$BACKEND_DIR/cert.pem" ] && [ -f "$BACKEND_DIR/key.pem" ]; then
    LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "xxx.xxx.xxx.xxx")
    echo ""
    echo "======================================"
    echo "  アクセス URL"
    echo "======================================"
    echo "  PC    : https://localhost:8443"
    echo "  スマホ : https://${LOCAL_IP}:8443"
    echo "  ※ 初回アクセス時にブラウザの証明書警告が出ます"
    echo "     Chrome: [詳細設定] → [アクセスする]"
    echo "     Safari: [詳細を表示] → [このWebサイトを閲覧]"
    echo "======================================"
    echo "  Ctrl+C で停止"
    echo ""
    uvicorn main:app --host 0.0.0.0 --port 8443 --ssl-certfile cert.pem --ssl-keyfile key.pem --reload
else
    echo "[WARNING] SSL証明書が生成できませんでした。HTTP モードで起動します"
    echo "[WARNING] HTTP ではスマホカメラが使用できません (HTTPS が必要)"
    echo "[INFO] アプリを起動中... http://localhost:8000"
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
fi
