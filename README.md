# 荷物管理Webアプリ

IBM i（DB2）の受注残データ（RJU1）を活用した発送業務管理システム。

## システム構成

| レイヤー | 技術 |
|---------|------|
| バックエンド | Python 3.11+ / FastAPI |
| データベース | SQLite（キャッシュ・ステータス管理） |
| IBM i 接続 | JDBC（JayDeBeApi + jt400.jar）読み取り専用 |
| フロントエンド | レスポンシブ HTML/CSS/JS（スマホ・PC対応） |

## ディレクトリ構成

```
Shipping-Management/
├── backend/
│   ├── main.py          # FastAPI アプリ
│   ├── database.py      # SQLite 設定・テーブル定義
│   ├── models.py        # Pydantic モデル
│   ├── auth.py          # JWT 認証
│   ├── ibmi.py          # IBM i JDBC 接続（デモモード対応）
│   ├── routes/
│   │   ├── shipments.py # 荷物一覧・詳細・ステータス更新 API
│   │   ├── sync.py      # IBM i 同期 API
│   │   └── labels.py    # 荷札PDF生成 API
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── index.html       # メイン画面（SPA）
│   ├── css/style.css    # スタイルシート
│   └── js/
│       ├── api.js       # API クライアント
│       ├── scanner.js   # バーコードスキャン
│       └── app.js       # メインアプリ
├── start.sh             # 起動スクリプト
└── README.md
```

## セットアップ

### 1. 環境変数設定

```bash
cp backend/.env.example backend/.env
# backend/.env を編集して IBM i 接続情報を設定
```

`.env` の主要設定：

```ini
IBMI_HOST=192.168.3.230
IBMI_USER=your_user
IBMI_PASSWORD=your_password
IBMI_LIBRARY=TREED
IBMI_TABLE=RJU1
IBMI_DRIVER_PATH=/opt/jt400/jt400.jar
DEMO_MODE=false   # 本番時は false
APP_SECRET_KEY=your-secret-key
```

### 2. jt400.jar の配置（本番時）

IBM i JDBC ドライバを配置してください：

```bash
mkdir -p /opt/jt400
cp jt400.jar /opt/jt400/
```

### 3. 起動

```bash
chmod +x start.sh
./start.sh
```

または手動で：

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

ブラウザで `http://localhost:8000` にアクセス。

## デモモード

`DEMO_MODE=true`（デフォルト）でサンプルデータを使用して動作確認できます。IBM i に接続不要。

## ログイン

| ユーザー | パスワード | 権限 |
|---------|-----------|------|
| admin | admin123 | 管理者 |
| user1 | user123 | 発送担当1（T001） |
| user2 | user123 | 発送担当2（T002） |
| user3 | user123 | 発送担当3（T003） |

## API エンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| POST | /api/auth/login | ログイン |
| GET | /api/shipments | 荷物一覧（フィルター対応） |
| GET | /api/shipments/{denno} | 荷物詳細 |
| PUT | /api/shipments/{denno}/status | ステータス更新 |
| GET | /api/scan/{barcode} | バーコード検索 |
| POST | /api/sync | IBM i 同期 |
| GET | /api/shipments/{denno}/label | 荷札PDF生成 |

API ドキュメント: `http://localhost:8000/docs`

## ステータス管理

| ステータス | 判定 |
|-----------|------|
| 未処理 | JUCHU='1' かつ SYKDY=0 |
| 梱包中 | アプリ側で手動セット（SQLiteのみ） |
| 出荷済 | SYKDY > 0 かつ URIAG='0' |
| 納品完了 | URIAG='1' |

> IBM i への書き込みは一切行いません（読み取り専用）。
