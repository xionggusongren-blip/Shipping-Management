from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from ..database import get_db_conn
from ..models import StatusUpdate
from ..ibmi import ibmi_date_to_str

router = APIRouter()


def _compute_status(row: dict) -> str:
    """ステータス自動判定ロジック（要件定義書 3.3）"""
    app_status = row.get("app_status")
    if app_status == "梱包中":
        return "梱包中"
    sykdy = int(row.get("sykdy") or 0)
    uriag = str(row.get("uriag") or "0").strip()
    if uriag == "1":
        return "納品完了"
    if sykdy > 0:
        return "出荷済"
    return "未処理"


def _row_to_dict(row) -> dict:
    d = dict(row)
    d["status"] = _compute_status(d)
    d["nodayu_str"] = ibmi_date_to_str(d.get("nodayu"))
    d["nodays_str"] = ibmi_date_to_str(d.get("nodays"))
    d["sykdy_str"] = ibmi_date_to_str(d.get("sykdy"))
    return d


@router.get("/shipments")
def list_shipments(
    tanto: Optional[str] = Query(None, description="担当者コード"),
    ucod: Optional[int] = Query(None, description="得意先コード"),
    status: Optional[str] = Query(None, description="ステータス"),
    date_from: Optional[str] = Query(None, description="納期From (YYYY/MM/DD)"),
    date_to: Optional[str] = Query(None, description="納期To (YYYY/MM/DD)"),
):
    conn = get_db_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM shipments ORDER BY nodayu, denno"
        ).fetchall()
    finally:
        conn.close()

    result = [_row_to_dict(r) for r in rows]

    if tanto:
        result = [s for s in result if (s.get("tanto") or "").strip() == tanto.strip()]
    if ucod:
        result = [s for s in result if s.get("ucod") == ucod]
    if status:
        result = [s for s in result if s.get("status") == status]

    return result


@router.get("/shipments/{denno}")
def get_shipment(denno: int):
    conn = get_db_conn()
    try:
        row = conn.execute(
            "SELECT * FROM shipments WHERE denno = ?", (denno,)
        ).fetchone()
    finally:
        conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="伝票番号が見つかりません")
    return _row_to_dict(row)


@router.put("/shipments/{denno}/status")
def update_status(denno: int, body: StatusUpdate):
    """ステータス更新（アプリ側SQLiteのみ。梱包中のみ手動設定可）"""
    if body.status not in ("梱包中", "未処理"):
        raise HTTPException(
            status_code=400,
            detail="手動設定できるステータスは '梱包中' または '未処理' のみです",
        )

    conn = get_db_conn()
    try:
        row = conn.execute(
            "SELECT denno FROM shipments WHERE denno = ?", (denno,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="伝票番号が見つかりません")

        new_app_status = "梱包中" if body.status == "梱包中" else None
        conn.execute(
            "UPDATE shipments SET app_status = ? WHERE denno = ?",
            (new_app_status, denno),
        )
        conn.commit()
    finally:
        conn.close()

    return {"success": True, "denno": denno, "status": body.status}


@router.get("/scan/{barcode}")
def scan_barcode(barcode: str):
    """バーコード/QRスキャンで荷物を検索（UTNO1またはHCOD）"""
    conn = get_db_conn()
    try:
        row = conn.execute(
            "SELECT * FROM shipments WHERE TRIM(utno1) = ? OR CAST(hcod AS TEXT) = ?",
            (barcode.strip(), barcode.strip()),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        raise HTTPException(
            status_code=404, detail=f"バーコード '{barcode}' に対応する荷物が見つかりません"
        )
    return _row_to_dict(row)
