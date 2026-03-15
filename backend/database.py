"""SQLite データベース設定"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./shipping.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class ShipmentCache(Base):
    """IBM i から取得したデータのキャッシュ"""
    __tablename__ = "shipment_cache"

    denno = Column(Integer, primary_key=True, index=True)
    tanto = Column(String(4))
    ucod = Column(Integer)
    hcod = Column(Integer)
    hname = Column(String(32))
    hnm2 = Column(String(32))
    mnmm = Column(String(20))
    mkrcd = Column(String(5))
    mhnm = Column(String(20))
    suryo = Column(Integer)
    nodayu = Column(Integer)
    nodays = Column(Integer)
    sykdy = Column(Integer)
    haiso = Column(String(5))
    synm1 = Column(String(32))
    synm2 = Column(String(32))
    adr1t = Column(String(32))
    adr2t = Column(String(32))
    utno1 = Column(String(20))
    juchu = Column(String(1))
    uriag = Column(String(1))
    order_flg = Column(String(1))
    slcrt = Column(Integer)
    dtadd = Column(String(20))
    synced_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class ShipmentStatus(Base):
    """アプリ側ステータス管理（IBM i には書き込まない）"""
    __tablename__ = "shipment_status"

    denno = Column(Integer, primary_key=True, index=True)
    status = Column(String(20), default="未処理")  # 未処理 / 梱包中 / 出荷済 / 納品完了
    memo = Column(Text, default="")
    updated_by = Column(String(50))
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class User(Base):
    """ユーザー管理"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True)
    hashed_password = Column(String(255))
    display_name = Column(String(100))
    role = Column(String(20), default="operator")  # operator / admin
    tanto_code = Column(String(4))
    is_active = Column(Integer, default=1)


class SyncLog(Base):
    """同期ログ"""
    __tablename__ = "sync_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    synced_at = Column(DateTime, default=datetime.now)
    record_count = Column(Integer, default=0)
    status = Column(String(20))  # success / error
    message = Column(Text)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
