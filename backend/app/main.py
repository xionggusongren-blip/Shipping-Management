import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import init_db
from .routers import shipments, sync, labels

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="荷物管理Webアプリ",
    version="1.0.0",
    description="IBM i DB2 (TREED.RJU1) 連携 荷物管理システム",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(shipments.router, prefix="/api", tags=["shipments"])
app.include_router(sync.router, prefix="/api", tags=["sync"])
app.include_router(labels.router, prefix="/api", tags=["labels"])


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


# フロントエンド静的ファイルを配信
_frontend = os.path.join(os.path.dirname(__file__), "../../frontend")
if os.path.isdir(_frontend):
    app.mount("/", StaticFiles(directory=_frontend, html=True), name="frontend")
