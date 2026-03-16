"""
IBM i (DB2) 接続モジュール
- 本番: pyodbc + IBM i Access ODBC Driver 経由で接続（jt400.jar 不要）
- デモ: DEMO_MODE=true 時はサンプルデータを返す
"""
import os
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
IBMI_HOST     = os.getenv("IBMI_HOST", "192.168.3.230")
IBMI_USER     = os.getenv("IBMI_USER", "")
IBMI_PASSWORD = os.getenv("IBMI_PASSWORD", "")
IBMI_LIBRARY  = os.getenv("IBMI_LIBRARY", "TREED")
IBMI_TABLE    = os.getenv("IBMI_TABLE", "RJU1")

QUERY = f"""
SELECT
    DENNO, TANTO, UCOD, HCOD,
    CAST(HNAME AS VARGRAPHIC(60) CCSID 1200) AS HNAME,
    HNM2, MNMM, MKRCD, MHNM, SURYO,
    NODAYU, NODAYS, SYKDY, HAISO,
    CAST(SYNM1 AS VARGRAPHIC(60) CCSID 1200) AS SYNM1,
    CAST(SYNM2 AS VARGRAPHIC(60) CCSID 1200) AS SYNM2,
    ADR1T, ADR2T,
    UTNO1, JUCHU, URIAG, ORDER,
    SLCRT, DTADD
FROM {IBMI_LIBRARY}.{IBMI_TABLE}
WHERE RJU1D <> '1'
  AND URIAG <> '1'
ORDER BY NODAYU, DENNO
"""

COLUMNS = [
    "denno", "tanto", "ucod", "hcod", "hname", "hnm2",
    "mnmm", "mkrcd", "mhnm", "suryo",
    "nodayu", "nodays", "sykdy", "haiso",
    "synm1", "synm2", "adr1t", "adr2t",
    "utno1", "juchu", "uriag", "order_flg",
    "slcrt", "dtadd",
]


def fetch_from_ibmi() -> List[Dict[str, Any]]:
    """IBM i RJU1 テーブルからデータを取得する"""
    if DEMO_MODE:
        logger.info("DEMO MODE: IBM i 接続をスキップし、サンプルデータを返します")
        return _get_demo_data()

    return _fetch_via_odbc()


def _fetch_via_odbc() -> List[Dict[str, Any]]:
    """pyodbc + IBM i Access ODBC Driver で接続"""
    try:
        import pyodbc
    except ImportError:
        raise RuntimeError("pyodbc がインストールされていません。pip install pyodbc を実行してください")

    conn_str = (
        f"DRIVER={{IBM i Access ODBC Driver}};"
        f"SYSTEM={IBMI_HOST};"
        f"UID={IBMI_USER};"
        f"PWD={IBMI_PASSWORD};"
        f"DBQ=QGPL TREEW {IBMI_LIBRARY};"
        f"UNICODESQL=1"
    )

    try:
        conn = pyodbc.connect(conn_str, timeout=30)
        cursor = conn.cursor()
        cursor.execute(QUERY)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"IBM i ODBC 接続エラー: {e}")
        raise

    result = []
    for row in rows:
        record = dict(zip(COLUMNS, row))
        # 数値フィールドを int に変換
        for key in ["denno", "ucod", "hcod", "suryo", "nodayu", "nodays", "sykdy", "slcrt"]:
            if record.get(key) is not None:
                try:
                    record[key] = int(record[key])
                except (ValueError, TypeError):
                    record[key] = 0
        # 文字列フィールドをトリム
        for key in COLUMNS:
            if isinstance(record.get(key), str):
                record[key] = record[key].strip()
        result.append(record)

    logger.info(f"IBM i から {len(result)} 件取得しました")
    return result


def _get_demo_data() -> List[Dict[str, Any]]:
    """デモ用サンプルデータ"""
    return [
        {
            "denno": 1260001, "tanto": "T001", "ucod": 100001, "hcod": 2000001,
            "hname": "電動モーター A型", "hnm2": "AC-200V 50Hz", "mnmm": "山田電機",
            "mkrcd": "YM001", "mhnm": "YM-MOT-A001", "suryo": 5,
            "nodayu": 1260315, "nodays": 1260310, "sykdy": 0, "haiso": "YAMTO",
            "synm1": "株式会社東京商事", "synm2": "資材部",
            "adr1t": "東京都千代田区丸の内1-1-1", "adr2t": "東京商事ビル3F",
            "utno1": "TK-2026-00123", "juchu": "1", "uriag": "0", "order_flg": "0",
            "slcrt": 1001, "dtadd": "要冷暗所保管",
        },
        {
            "denno": 1260002, "tanto": "T002", "ucod": 100002, "hcod": 2000002,
            "hname": "制御基板 B型", "hnm2": "DC-24V 制御用", "mnmm": "鈴木電子",
            "mkrcd": "SK002", "mhnm": "SK-PCB-B002", "suryo": 10,
            "nodayu": 1260320, "nodays": 1260318, "sykdy": 0, "haiso": "SAGAWA",
            "synm1": "大阪精密工業株式会社", "synm2": "",
            "adr1t": "大阪府大阪市北区梅田2-2-2", "adr2t": "",
            "utno1": "OS-2026-00456", "juchu": "1", "uriag": "0", "order_flg": "1",
            "slcrt": 1002, "dtadd": "",
        },
        {
            "denno": 1260003, "tanto": "T001", "ucod": 100003, "hcod": 2000003,
            "hname": "センサーユニット C型", "hnm2": "温度・湿度センサー", "mnmm": "中村計測",
            "mkrcd": "NK003", "mhnm": "NK-SEN-C003", "suryo": 20,
            "nodayu": 1260312, "nodays": 1260312, "sykdy": 1260311, "haiso": "FUKUTU",
            "synm1": "名古屋自動車部品株式会社", "synm2": "技術部",
            "adr1t": "愛知県名古屋市中村区名駅3-3-3", "adr2t": "名古屋部品センター",
            "utno1": "NA-2026-00789", "juchu": "1", "uriag": "0", "order_flg": "0",
            "slcrt": 1001, "dtadd": "精密機器注意",
        },
        {
            "denno": 1260004, "tanto": "T003", "ucod": 100004, "hcod": 2000004,
            "hname": "油圧バルブ D型", "hnm2": "最大圧力 21MPa", "mnmm": "伊藤油機",
            "mkrcd": "IT004", "mhnm": "IT-VLV-D004", "suryo": 3,
            "nodayu": 1260325, "nodays": 1260322, "sykdy": 0, "haiso": "YAMTO",
            "synm1": "福岡重工業株式会社", "synm2": "製造部",
            "adr1t": "福岡県福岡市博多区博多駅前4-4-4", "adr2t": "",
            "utno1": "FK-2026-01012", "juchu": "0", "uriag": "0", "order_flg": "0",
            "slcrt": 1003, "dtadd": "重量物",
        },
        {
            "denno": 1260005, "tanto": "T002", "ucod": 100005, "hcod": 2000005,
            "hname": "ギアボックス E型", "hnm2": "減速比 1/10", "mnmm": "小林機械",
            "mkrcd": "KB005", "mhnm": "KB-GBX-E005", "suryo": 2,
            "nodayu": 1260314, "nodays": 1260314, "sykdy": 1260312, "haiso": "SAGAWA",
            "synm1": "仙台機械設備株式会社", "synm2": "",
            "adr1t": "宮城県仙台市青葉区中央5-5-5", "adr2t": "機械設備センター",
            "utno1": "SE-2026-01345", "juchu": "1", "uriag": "0", "order_flg": "0",
            "slcrt": 1002, "dtadd": "取扱注意",
        },
        {
            "denno": 1260006, "tanto": "T001", "ucod": 100001, "hcod": 2000006,
            "hname": "電磁クラッチ F型", "hnm2": "DC-24V 10Nm", "mnmm": "山田電機",
            "mkrcd": "YM001", "mhnm": "YM-CLC-F006", "suryo": 8,
            "nodayu": 1260330, "nodays": 1260328, "sykdy": 0, "haiso": "YAMTO",
            "synm1": "株式会社東京商事", "synm2": "資材部",
            "adr1t": "東京都千代田区丸の内1-1-1", "adr2t": "東京商事ビル3F",
            "utno1": "TK-2026-01678", "juchu": "1", "uriag": "0", "order_flg": "1",
            "slcrt": 1001, "dtadd": "",
        },
    ]
