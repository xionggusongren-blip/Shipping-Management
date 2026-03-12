from pydantic import BaseModel
from typing import Optional


class Shipment(BaseModel):
    denno: int
    tanto: Optional[str] = None
    ucod: Optional[int] = None
    hcod: Optional[int] = None
    hname: Optional[str] = None
    hnm2: Optional[str] = None
    mnmm: Optional[str] = None
    mkrcd: Optional[str] = None
    mhnm: Optional[str] = None
    suryo: Optional[float] = None
    nodayu: Optional[int] = None
    nodays: Optional[int] = None
    sykdy: Optional[int] = None
    haiso: Optional[str] = None
    synm1: Optional[str] = None
    synm2: Optional[str] = None
    adr1t: Optional[str] = None
    adr2t: Optional[str] = None
    utno1: Optional[str] = None
    juchu: Optional[str] = None
    uriag: Optional[str] = None
    order_col: Optional[str] = None
    slcrt: Optional[int] = None
    dtadd: Optional[str] = None
    # アプリ側で管理
    app_status: Optional[str] = None
    synced_at: Optional[str] = None
    # 計算フィールド
    status: Optional[str] = None
    nodayu_str: Optional[str] = None
    nodays_str: Optional[str] = None
    sykdy_str: Optional[str] = None


class StatusUpdate(BaseModel):
    status: str  # '梱包中' または '未処理'


class SyncResult(BaseModel):
    success: bool
    message: str
    count: int = 0
