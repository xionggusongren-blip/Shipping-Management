import sqlite3
from .config import settings


def get_db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with sqlite3.connect(settings.SQLITE_DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS shipments (
                denno       INTEGER PRIMARY KEY,
                tanto       TEXT,
                ucod        INTEGER,
                hcod        INTEGER,
                hname       TEXT,
                hnm2        TEXT,
                mnmm        TEXT,
                mkrcd       TEXT,
                mhnm        TEXT,
                suryo       REAL,
                nodayu      INTEGER,
                nodays      INTEGER,
                sykdy       INTEGER,
                haiso       TEXT,
                synm1       TEXT,
                synm2       TEXT,
                adr1t       TEXT,
                adr2t       TEXT,
                utno1       TEXT,
                juchu       TEXT,
                uriag       TEXT,
                order_col   TEXT,
                slcrt       INTEGER,
                dtadd       TEXT,
                app_status  TEXT DEFAULT NULL,
                synced_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
