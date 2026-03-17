"""荷物一覧・詳細・ステータス更新 API"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, distinct
from typing import Optional, List
from datetime import datetime

from database import get_db, ShipmentCache, ShipmentStatus
from models import ShipmentListItem, ShipmentResponse, StatusUpdate, ibmi_date_to_str
from auth import get_current_user, User

router = APIRouter()


def _build_response(cache: ShipmentCache, status_rec: Optional[ShipmentStatus]) -> dict:
    data = {col: getattr(cache, col) for col in cache.__table__.columns.keys()}
    data["status"] = status_rec.status if status_rec else _auto_status(cache)
    data["memo"] = status_rec.memo if status_rec else ""
    data["updated_by"] = status_rec.updated_by if status_rec else None
    data["updated_at"] = status_rec.updated_at if status_rec else None
    data["nodayu_str"] = ibmi_date_to_str(cache.nodayu)
    data["nodays_str"] = ibmi_date_to_str(cache.nodays)
    data["sykdy_str"] = ibmi_date_to_str(cache.sykdy)
    return data


def _auto_status(cache: ShipmentCache) -> str:
    """IBM i フラグからステータスを自動判定"""
    if cache.uriag == "1":
        return "納品完了"
    if cache.sykdy and cache.sykdy > 0:
        return "出荷済"
    if cache.juchu == "1":
        return "未処理"
    return "未処理"


@router.get("/tantos")
def get_tantos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """担当者コード一覧を返す（Z999除外）"""
    rows = (
        db.query(distinct(ShipmentCache.tanto))
        .filter(
            ShipmentCache.tanto.isnot(None),
            ShipmentCache.tanto != "",
            ~ShipmentCache.tanto.like("Z999%"),
        )
        .order_by(ShipmentCache.tanto)
        .all()
    )
    return [{"tanto": r[0]} for r in rows]


@router.get("/shipments", response_model=List[dict])
def get_shipments(
    tanto: Optional[str] = Query(None, description="担当者コードで絞り込み"),
    ucod: Optional[int] = Query(None, description="得意先コードで絞り込み"),
    status: Optional[str] = Query(None, description="ステータスで絞り込み"),
    date_from: Optional[str] = Query(None, description="納期FROM (YYYY/MM/DD)"),
    date_to: Optional[str] = Query(None, description="納期TO (YYYY/MM/DD)"),
    keyword: Optional[str] = Query(None, description="品名・出荷先名フリーワード"),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(ShipmentCache).filter(~ShipmentCache.tanto.like("Z999%"))

    if tanto:
        # tanto フィールドは「E102 山田太郎」形式のため前方一致で絞り込む
        query = query.filter(ShipmentCache.tanto.like(f"{tanto}%"))
    if ucod:
        query = query.filter(ShipmentCache.ucod == ucod)
    if keyword:
        query = query.filter(
            or_(
                ShipmentCache.hname.contains(keyword),
                ShipmentCache.synm1.contains(keyword),
                ShipmentCache.synm2.contains(keyword),
                ShipmentCache.tanto.contains(keyword),
            )
        )

    caches = query.order_by(ShipmentCache.nodayu, ShipmentCache.denno).all()

    # ステータスをマージ
    status_map = {
        s.denno: s
        for s in db.query(ShipmentStatus).filter(
            ShipmentStatus.denno.in_([c.denno for c in caches])
        ).all()
    }

    results = []
    for c in caches:
        s = status_map.get(c.denno)
        computed_status = s.status if s else _auto_status(c)

        if status and computed_status != status:
            continue

        results.append({
            "denno": c.denno,
            "tanto": (c.tanto or "").strip(),
            "ucod": c.ucod,
            "hname": c.hname,
            "synm1": c.synm1,
            "suryo": c.suryo,
            "nodayu": c.nodayu,
            "nodayu_str": ibmi_date_to_str(c.nodayu),
            "haiso": c.haiso,
            "status": computed_status,
        })

    total = len(results)
    return results[offset: offset + limit]


@router.get("/shipments/{denno}")
def get_shipment_detail(
    denno: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cache = db.query(ShipmentCache).filter(ShipmentCache.denno == denno).first()
    if not cache:
        raise HTTPException(status_code=404, detail="荷物が見つかりません")

    status_rec = db.query(ShipmentStatus).filter(ShipmentStatus.denno == denno).first()
    return _build_response(cache, status_rec)


@router.put("/shipments/{denno}/status")
def update_status(
    denno: int,
    body: StatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cache = db.query(ShipmentCache).filter(ShipmentCache.denno == denno).first()
    if not cache:
        raise HTTPException(status_code=404, detail="荷物が見つかりません")

    valid_statuses = ["未処理", "梱包中", "出荷済", "納品完了"]
    if body.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"無効なステータスです。有効値: {valid_statuses}")

    status_rec = db.query(ShipmentStatus).filter(ShipmentStatus.denno == denno).first()
    if status_rec:
        status_rec.status = body.status
        status_rec.memo = body.memo or ""
        status_rec.updated_by = body.updated_by or current_user.display_name
        status_rec.updated_at = datetime.now()
    else:
        status_rec = ShipmentStatus(
            denno=denno,
            status=body.status,
            memo=body.memo or "",
            updated_by=body.updated_by or current_user.display_name,
        )
        db.add(status_rec)

    db.commit()
    return {"success": True, "denno": denno, "status": body.status}


@router.get("/scan/{barcode}")
def scan_barcode(
    barcode: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """バーコード値で荷物を検索（UTNO1、HCOD、または DENNO）"""
    b = barcode.strip()
    # UTNO1 で検索
    cache = db.query(ShipmentCache).filter(ShipmentCache.utno1 == b).first()
    if not cache:
        # 数値の場合: DENNO または HCOD で検索
        try:
            int_val = int(b)
            cache = db.query(ShipmentCache).filter(ShipmentCache.denno == int_val).first()
            if not cache:
                cache = db.query(ShipmentCache).filter(ShipmentCache.hcod == int_val).first()
        except ValueError:
            pass

    if not cache:
        raise HTTPException(status_code=404, detail=f"バーコード '{b}' に一致する荷物が見つかりません")

    status_rec = db.query(ShipmentStatus).filter(ShipmentStatus.denno == cache.denno).first()
    return _build_response(cache, status_rec)
