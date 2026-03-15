"""Pydantic モデル定義"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


def ibmi_date_to_str(val) -> Optional[str]:
    """CYYMMDD形式 (DECIMAL 7) を YYYY/MM/DD に変換"""
    if not val or val == 0:
        return None
    s = str(int(val)).zfill(7)
    c, yy, mm, dd = s[0], s[1:3], s[3:5], s[5:7]
    year = 1900 + int(c) * 100 + int(yy)
    return f"{year}/{mm}/{dd}"


class ShipmentBase(BaseModel):
    denno: int
    tanto: Optional[str] = None
    ucod: Optional[int] = None
    hcod: Optional[int] = None
    hname: Optional[str] = None
    hnm2: Optional[str] = None
    mnmm: Optional[str] = None
    mkrcd: Optional[str] = None
    mhnm: Optional[str] = None
    suryo: Optional[int] = None
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
    order_flg: Optional[str] = None
    slcrt: Optional[int] = None
    dtadd: Optional[str] = None

    class Config:
        from_attributes = True


class ShipmentResponse(ShipmentBase):
    """荷物詳細レスポンス（日付変換済み）"""
    status: str = "未処理"
    memo: str = ""
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    synced_at: Optional[datetime] = None

    # 変換済み日付フィールド
    nodayu_str: Optional[str] = None
    nodays_str: Optional[str] = None
    sykdy_str: Optional[str] = None


class ShipmentListItem(BaseModel):
    """荷物一覧用軽量モデル"""
    denno: int
    tanto: Optional[str] = None
    ucod: Optional[int] = None
    hname: Optional[str] = None
    synm1: Optional[str] = None
    suryo: Optional[int] = None
    nodayu: Optional[int] = None
    nodayu_str: Optional[str] = None
    haiso: Optional[str] = None
    status: str = "未処理"

    class Config:
        from_attributes = True


class StatusUpdate(BaseModel):
    status: str  # 未処理 / 梱包中 / 出荷済 / 納品完了
    memo: Optional[str] = ""
    updated_by: Optional[str] = None


class UserCreate(BaseModel):
    username: str
    password: str
    display_name: str
    role: str = "operator"
    tanto_code: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict


class SyncResult(BaseModel):
    status: str
    record_count: int
    message: str
    synced_at: datetime
