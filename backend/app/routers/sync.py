import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException
from ..database import get_db_conn
from ..ibmi import fetch_rju1_data
from ..models import SyncResult

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/sync", response_model=SyncResult)
def sync_from_ibmi():
    """IBM i RJU1 から最新データを取得してSQLiteを更新"""
    try:
        rows = fetch_rju1_data()
    except Exception as e:
        logger.error(f"IBM i 同期失敗: {e}")
        raise HTTPException(status_code=503, detail=f"IBM i 接続失敗: {str(e)}")

    conn = get_db_conn()
    try:
        now = datetime.now().isoformat()
        for row in rows:
            conn.execute(
                """
                INSERT INTO shipments (
                    denno, tanto, ucod, hcod, hname, hnm2, mnmm, mkrcd, mhnm,
                    suryo, nodayu, nodays, sykdy, haiso, synm1, synm2,
                    adr1t, adr2t, utno1, juchu, uriag, order_col, slcrt, dtadd,
                    synced_at
                ) VALUES (
                    :denno, :tanto, :ucod, :hcod, :hname, :hnm2, :mnmm, :mkrcd, :mhnm,
                    :suryo, :nodayu, :nodays, :sykdy, :haiso, :synm1, :synm2,
                    :adr1t, :adr2t, :utno1, :juchu, :uriag, :order_col, :slcrt, :dtadd,
                    :synced_at
                )
                ON CONFLICT(denno) DO UPDATE SET
                    tanto=excluded.tanto, ucod=excluded.ucod, hcod=excluded.hcod,
                    hname=excluded.hname, hnm2=excluded.hnm2, mnmm=excluded.mnmm,
                    mkrcd=excluded.mkrcd, mhnm=excluded.mhnm, suryo=excluded.suryo,
                    nodayu=excluded.nodayu, nodays=excluded.nodays, sykdy=excluded.sykdy,
                    haiso=excluded.haiso, synm1=excluded.synm1, synm2=excluded.synm2,
                    adr1t=excluded.adr1t, adr2t=excluded.adr2t, utno1=excluded.utno1,
                    juchu=excluded.juchu, uriag=excluded.uriag, order_col=excluded.order_col,
                    slcrt=excluded.slcrt, dtadd=excluded.dtadd, synced_at=excluded.synced_at
                """,
                {**row, "synced_at": now},
            )
        conn.commit()
    finally:
        conn.close()

    count = len(rows)
    return SyncResult(success=True, message=f"{count} 件のデータを同期しました", count=count)
