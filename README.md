# 荷物管理Webアプリ

IBM i DB2（TREED.RJU1）と連携した発送業務管理システム。

## システム構成

| レイヤー | 技術 |
|---|---|
| バックエンド | Python + FastAPI |
| DB接続 | JDBC (JayDeBeApi + jt400.jar) 読み取り専用 |
| ローカルDB | SQLite |
| フロントエンド | レスポンシブHTML+JS（スマホ・PC対応） |

## ディレクトリ構成

```
Shipping-Management/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPIアプリ
│   │   ├── config.py        # 環境変数設定
│   │   ├── database.py      # SQLite接続・初期化
│   │   ├── ibmi.py          # IBM i JDBC接続（モック対応）
│   │   ├── models.py        # Pydanticモデル
│   │   └── routers/
│   │       ├── shipments.py # 荷物一覧・詳細・ステータス更新
│   │       ├── sync.py      # IBM i 同期
│   │       └── labels.py    # 荷札HTML生成
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    └── index.html           # レスポンシブSPA
```

## セットアップ

### 1. 環境設定

```bash
cd backend
cp .env.example .env
# .env を編集して IBM i 接続情報を設定
```

### 2. jt400.jar の配置

IBM i 接続用JDBCドライバを取得し、`.env` の `JT400_JAR_PATH` に設定：
```
JT400_JAR_PATH=C:/tools/jt400.jar
```

### 3. Python依存パッケージのインストール

```bash
cd backend
pip install -r requirements.txt
```

> **注意:** JayDeBeApi / JPype1 は Java (JDK 11+) が必要です。
> jt400.jar が無い場合は自動的にモックデータで動作します。

### 4. 起動

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

ブラウザで `http://localhost:8000` にアクセス。

---

## REST API エンドポイント

| メソッド | URL | 説明 |
|---|---|---|
| GET | `/api/shipments` | 荷物一覧（フィルター: tanto, ucod, status） |
| GET | `/api/shipments/{denno}` | 荷物詳細 |
| PUT | `/api/shipments/{denno}/status` | ステータス更新（梱包中のみ） |
| GET | `/api/shipments/{denno}/label` | 荷札HTML（印刷用） |
| GET | `/api/scan/{barcode}` | バーコード検索（UTNO1/HCOD） |
| POST | `/api/sync` | IBM i RJU1 データ同期 |
| GET | `/api/health` | ヘルスチェック |

API仕様: `http://localhost:8000/docs`

---

## ステータス管理

| ステータス | 判定条件 |
|---|---|
| 未処理 | JUCHU='0' AND SYKDY=0 |
| 梱包中 | アプリ側SQLiteで管理（手動セット） |
| 出荷済 | SYKDY > 0 AND URIAG='0' |
| 納品完了 | URIAG='1'（一覧から除外） |

IBM i への書き込みは一切行いません（読み取り専用）。

---

## 開発フェーズ

- [x] **Phase 1**: DB接続・基本機能（荷物一覧・詳細・ステータス管理・荷札）
- [ ] **Phase 2**: バーコード/QRスキャン
- [ ] **Phase 3**: 荷札PDF生成
- [ ] **Phase 4**: 運用検証・UI改善
- [ ] **Phase 5**: ハンディターミナル対応
