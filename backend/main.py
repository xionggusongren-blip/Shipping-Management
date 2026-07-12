"""
荷物管理Webアプリ - FastAPI バックエンド
"""
# .env を最初に読み込む（他モジュールの import より先に実行する必要がある）
from dotenv import load_dotenv
load_dotenv(override=True)

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import get_db, init_db, SessionLocal
from auth import (
    verify_password, create_access_token, create_default_users,
    get_current_user, User,
)
from models import UserLogin, Token
from routes import shipments, sync, labels
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """起動時初期化"""
    logger.info(f"アプリケーション起動中... DEMO_MODE={os.getenv('DEMO_MODE')}")
    init_db()
    db = SessionLocal()
    try:
        create_default_users(db)
        # DEMO_MODE時は初回起動時に自動同期
        if os.getenv("DEMO_MODE", "true").lower() == "true":
            from routes.sync import _do_sync
            try:
                result = _do_sync(db, triggered_by="startup")
                logger.info(f"初期データ同期完了: {result['record_count']}件")
            except Exception as e:
                logger.warning(f"初期同期スキップ: {e}")
    finally:
        db.close()
    logger.info("起動完了")
    yield
    logger.info("アプリケーション終了")


app = FastAPI(
    title="荷物管理Webアプリ",
    description="IBM i RJU1 テーブルを活用した発送業務管理システム",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API ルーター登録
app.include_router(shipments.router, prefix="/api", tags=["荷物"])
app.include_router(sync.router, prefix="/api", tags=["同期"])
app.include_router(labels.router, prefix="/api", tags=["荷札"])


@app.post("/api/auth/login", response_model=Token, tags=["認証"])
def login(body: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザー名またはパスワードが正しくありません",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="このアカウントは無効です")

    token = create_access_token({"sub": user.username})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role,
            "tanto_code": user.tanto_code,
        },
    }


@app.get("/api/auth/me", tags=["認証"])
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "username": current_user.username,
        "display_name": current_user.display_name,
        "role": current_user.role,
        "tanto_code": current_user.tanto_code,
    }


@app.get("/api/health", tags=["システム"])
def health():
    return {"status": "ok", "demo_mode": os.getenv("DEMO_MODE", "true").lower() == "true"}


_NO_CACHE = "no-store, no-cache, must-revalidate, max-age=0"


def _no_cache_file(path: str, media_type: str) -> FileResponse:
    """キャッシュ無効ヘッダー付きでファイルを配信する"""
    resp = FileResponse(path, media_type=media_type)
    resp.headers["Cache-Control"] = _NO_CACHE
    return resp


# フロントエンド静的ファイルの配信
_frontend_abs = os.path.abspath(FRONTEND_DIR)
if os.path.exists(_frontend_abs):
    app.mount("/static", StaticFiles(directory=os.path.join(_frontend_abs, "css")), name="css")

    @app.get("/js/{filename:path}", include_in_schema=False)
    def serve_js(filename: str):
        path = os.path.join(_frontend_abs, "js", filename)
        if not os.path.exists(path):
            raise HTTPException(status_code=404)
        return _no_cache_file(path, "application/javascript")

    @app.get("/", include_in_schema=False)
    def serve_index():
        return _no_cache_file(os.path.join(_frontend_abs, "index.html"), "text/html")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        return _no_cache_file(os.path.join(_frontend_abs, "index.html"), "text/html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
