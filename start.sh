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

echo "[INFO] アプリを起動中... (http://localhost:8000)"
cd "$BACKEND_DIR"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
