"""荷物一覧・詳細・ステータス更新 API"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, distinct
from typing import Iterable, Optional, List, Dict
from datetime import datetime

from database import get_db, ShipmentCache, ShipmentStatus, CustomerCache
from models import StatusUpdate, ibmi_date_to_str
from auth import get_current_user, User

router = APIRouter()

# Z999 = 担当なしコード。一覧・フィルター候補の両方から除外する
TANTO_EXCLUDED_PREFIX = "Z999"

VALID_STATUSES = ["未処理", "梱包中", "出荷済", "納品完了"]


def _not_z999():
    """Z999（担当なし）を除外する SQLAlchemy フィルター条件"""
    return ~ShipmentCache.tanto.like(f"{TANTO_EXCLUDED_PREFIX}%")


def _customer_name_map(db: Session, ucods: Iterable[int]) -> Dict[int, str]:
    """得意先コード → 得意先名 のマップを返す"""
    ucods = {u for u in ucods if u}
    if not ucods:
        return {}
    rows = db.query(CustomerCache).filter(CustomerCache.ucod.in_(ucods)).all()
    return {r.ucod: r.uname or "" for r in rows}


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
    return "未処理"


@router.get("/customers")
def get_customers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """得意先一覧を返す（customer_cache → なければ shipment_cache の SYNM1 を使用）"""
    rows = db.query(CustomerCache).order_by(CustomerCache.ucod).all()
    if rows:
        return [{"ucod": r.ucod, "uname": r.uname or str(r.ucod)} for r in rows]

    # フォールバック: 荷物キャッシュの出荷先名を使用
    pairs = (
        db.query(ShipmentCache.ucod, ShipmentCache.synm1)
        .filter(ShipmentCache.ucod.isnot(None), _not_z999())
        .distinct()
        .order_by(ShipmentCache.ucod)
        .all()
    )
    seen: Dict[int, str] = {}
    for ucod, synm1 in pairs:
        if ucod and ucod not in seen:
            seen[ucod] = (synm1 or "").strip()
    return [{"ucod": k, "uname": v or str(k)} for k, v in seen.items()]


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
            _not_z999(),
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
    keyword: Optional[str] = Query(None, description="品名・出荷先名・担当者名フリーワード"),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(ShipmentCache).filter(_not_z999())

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

    customer_names = _customer_name_map(db, (c.ucod for c in caches))

    # アプリ側ステータスをマージ
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
            "uname": customer_names.get(c.ucod, ""),
            "hname": c.hname,
            "synm1": c.synm1,
            "suryo": c.suryo,
            "nodayu": c.nodayu,
            "nodayu_str": ibmi_date_to_str(c.nodayu),
            "haiso": c.haiso,
            "status": computed_status,
        })

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
    data = _build_response(cache, status_rec)
    data["uname"] = _customer_name_map(db, [cache.ucod]).get(cache.ucod, "")
    return data


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

    if body.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"無効なステータスです。有効値: {VALID_STATUSES}")

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
