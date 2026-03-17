"""IBM i データ同期 API"""
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from database import get_db, ShipmentCache, SyncLog
from ibmi import fetch_from_ibmi
from auth import require_admin, get_current_user, User

router = APIRouter()
logger = logging.getLogger(__name__)


def _do_sync(db: Session, triggered_by: str = "system") -> dict:
    """IBM i からデータを取得してSQLiteに保存"""
    started_at = datetime.now()
    try:
        rows = fetch_from_ibmi()

        # IBM i から取得した denno セット（重複除去）
        seen: set = set()
        valid_rows = []
        for row in rows:
            denno = row.get("denno")
            if denno is None or denno in seen:
                continue
            seen.add(denno)
            valid_rows.append(row)

        # IBM i に存在しなくなったレコードを削除（受注残から外れたもの）
        if seen:
            deleted = (
                db.query(ShipmentCache)
                .filter(~ShipmentCache.denno.in_(seen))
                .delete(synchronize_session=False)
            )
            if deleted:
                logger.info(f"削除済みレコード: {deleted}件（IBM i から消えたもの）")

        # INSERT / UPDATE（モデルに存在するカラムのみ渡す）
        cache_cols = {c.name for c in ShipmentCache.__table__.columns}
        for row in valid_rows:
            safe_row = {k: v for k, v in row.items() if k in cache_cols}
            safe_row["synced_at"] = datetime.now()
            obj = ShipmentCache(**safe_row)
            db.merge(obj)

        db.commit()
        count = len(valid_rows)

        log = SyncLog(
            synced_at=started_at,
            record_count=count,
            status="success",
            message=f"{count}件を同期しました（実行者: {triggered_by}）",
        )
        db.add(log)
        db.commit()

        logger.info(f"同期完了: {count}件")
        return {"status": "success", "record_count": count, "message": f"{count}件を同期しました", "synced_at": started_at}

    except Exception as e:
        error_msg = str(e)
        logger.error(f"同期エラー: {error_msg}")
        log = SyncLog(
            synced_at=started_at,
            record_count=0,
            status="error",
            message=error_msg,
        )
        db.add(log)
        db.commit()
        raise


@router.post("/sync")
def sync_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """IBM i RJU1 から最新データを同期する"""
    result = _do_sync(db, triggered_by=current_user.username)
    return result


@router.get("/sync/logs")
def get_sync_logs(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """同期ログを取得する"""
    logs = db.query(SyncLog).order_by(SyncLog.synced_at.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "synced_at": l.synced_at,
            "record_count": l.record_count,
            "status": l.status,
            "message": l.message,
        }
        for l in logs
    ]


@router.get("/sync/status")
def get_sync_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """最終同期情報を返す"""
    last = db.query(SyncLog).filter(SyncLog.status == "success").order_by(SyncLog.synced_at.desc()).first()
    total = db.query(ShipmentCache).count()
    return {
        "last_sync": last.synced_at if last else None,
        "record_count": total,
        "status": last.status if last else "未実行",
    }
