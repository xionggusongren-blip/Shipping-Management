# 荷物管理Webアプリ

IBM i（DB2）の受注残データ（TREED.RJU1）を活用した発送業務管理システム。
Python + FastAPI バックエンド / レスポンシブ Web フロントエンド（スマホ・PC 対応）

---

## システム構成

| レイヤー | 技術 |
|---------|------|
| バックエンド | Python 3.11+ / FastAPI |
| データベース | SQLite（キャッシュ・ステータス管理） |
| IBM i 接続 | JDBC（JayDeBeApi + jt400.jar）読み取り専用 |
| フロントエンド | HTML / CSS / JavaScript（スマホ対応） |

---

## ディレクトリ構成

```
Shipping-Management\
├── backend\
│   ├── main.py          # FastAPI アプリ本体
│   ├── database.py      # SQLite テーブル定義
│   ├── models.py        # Pydantic モデル・日付変換
│   ├── auth.py          # JWT 認証（bcrypt）
│   ├── ibmi.py          # IBM i JDBC 接続（デモモード内蔵）
│   ├── routes\
│   │   ├── shipments.py # 荷物一覧・詳細・ステータス更新・バーコード検索
│   │   ├── sync.py      # IBM i データ同期
│   │   └── labels.py    # 荷札 PDF 生成
│   ├── requirements.txt
│   └── .env.example     # 設定テンプレート
├── frontend\
│   ├── index.html       # メイン画面（SPA）
│   ├── css\style.css    # レスポンシブスタイル
│   └── js\
│       ├── api.js       # REST API クライアント
│       ├── scanner.js   # バーコードスキャン（html5-qrcode）
│       └── app.js       # メインアプリロジック
├── install.bat          # 初回セットアップ（仮想環境・依存関係）
├── start.bat            # アプリ起動
└── README.md
```

---

## セットアップ手順（Windows）

### 前提条件

- **Python 3.11 以上** がインストールされていること
  → https://www.python.org/downloads/
  ※ インストール時に **「Add Python to PATH」** にチェックを入れること

- **jt400.jar** を入手して任意のフォルダに配置すること（IBM i 本番接続時のみ必要）
  → 例: `C:\jt400\jt400.jar`

---

### Step 1: 初回セットアップ

エクスプローラーで `install.bat` をダブルクリック（または右クリック → 管理者として実行）。

```
install.bat
```

自動的に以下を実行します：
1. Python バージョン確認
2. 仮想環境 `.venv` 作成
3. 依存ライブラリ（FastAPI, SQLAlchemy 等）インストール
4. `backend\.env` ファイルを `.env.example` からコピー

---

### Step 2: 環境変数の設定

`backend\.env` をメモ帳などで開いて編集します：

```ini
# IBM i 接続情報
IBMI_HOST=192.168.3.230
IBMI_USER=your_user
IBMI_PASSWORD=your_password
IBMI_LIBRARY=TREED
IBMI_TABLE=RJU1
IBMI_DRIVER_PATH=C:\jt400\jt400.jar

# アプリ設定（必ず変更してください）
APP_SECRET_KEY=your-random-secret-key-here

# デモモード: IBM i 未接続でサンプルデータ表示 → true
#             IBM i 本番接続する場合               → false
DEMO_MODE=true
```

> ⚠ `.env` ファイルには機密情報が含まれます。Git にコミットしないでください（.gitignore で除外済み）。

---

### Step 3: アプリ起動

`start.bat` をダブルクリック。

```
start.bat
```

コマンドプロンプトに以下が表示されたら起動成功です：

```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

ブラウザで以下にアクセス：

```
http://localhost:8000
```

---

### Step 4: ログイン

| ユーザー名 | パスワード | 権限 | 担当コード |
|-----------|-----------|------|-----------|
| admin | admin123 | 管理者 | - |
| user1 | user123 | 発送担当 | T001 |
| user2 | user123 | 発送担当 | T002 |
| user3 | user123 | 発送担当 | T003 |

> 初回ログイン後、パスワードの変更を推奨します。

---

## IBM i 本番接続手順

1. `backend\.env` の `DEMO_MODE` を `false` に変更
2. `IBMI_USER` / `IBMI_PASSWORD` に読み取り専用ユーザーの認証情報を設定
3. `IBMI_DRIVER_PATH` に jt400.jar の **フルパス** を設定（例: `C:\jt400\jt400.jar`）
4. `start.bat` で再起動
5. 画面右上の「🔄 同期」ボタンを押してデータを取得

> IBM i への書き込みは一切行いません（SELECT 権限のみ使用）。

---

## API エンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| POST | /api/auth/login | ログイン（JWT トークン取得） |
| GET | /api/auth/me | ログイン中ユーザー情報 |
| GET | /api/shipments | 荷物一覧（フィルター: tanto, status, keyword） |
| GET | /api/shipments/{denno} | 荷物詳細（伝票番号指定） |
| PUT | /api/shipments/{denno}/status | ステータス更新（SQLite のみ） |
| GET | /api/scan/{barcode} | バーコード検索（UTNO1 または HCOD） |
| POST | /api/sync | IBM i RJU1 から最新データ同期 |
| GET | /api/sync/status | 最終同期情報 |
| GET | /api/sync/logs | 同期ログ一覧 |
| GET | /api/shipments/{denno}/label | 荷札 PDF 生成・ダウンロード |
| GET | /api/health | サーバー疎通確認 |

API ドキュメント（Swagger UI）: `http://localhost:8000/docs`

---

## ステータス管理

| ステータス | 判定条件 |
|-----------|---------|
| 未処理 | JUCHU='1' かつ SYKDY=0 |
| 梱包中 | アプリ側で手動設定（SQLite のみ。IBM i には反映しない） |
| 出荷済 | SYKDY > 0 かつ URIAG='0' |
| 納品完了 | URIAG='1' |

---

## トラブルシューティング

### `pip` が認識されない
Python インストール時に「Add Python to PATH」が未チェックです。
Python を再インストールして PATH を通してください。

### `uvicorn` が認識されない
`install.bat` を再実行してください。

### IBM i に接続できない
- `IBMI_HOST` が正しいか確認
- jt400.jar のパスに日本語・スペースが含まれていないか確認
- IBM i ユーザーに SELECT 権限があるか確認
- ファイアウォールでポート 446（AS/400 JDBC）が開いているか確認

### 画面が真っ白になる
ブラウザのキャッシュをクリア（Ctrl+Shift+R）してください。

---

## 開発フェーズ

| フェーズ | 内容 | 状態 |
|---------|------|------|
| Phase 1 | DB接続・荷物一覧・詳細・ステータス管理 | ✅ 完了 |
| Phase 2 | バーコード/QRスキャン | ✅ 実装済み |
| Phase 3 | 荷札 PDF 印刷 | ✅ 実装済み |
| Phase 4 | 運用検証・UI改善 | 🔄 検証中 |
| Phase 5 | ハンディターミナル対応 | 📋 計画中 |

---

作成：情報システム部　2026年3月
