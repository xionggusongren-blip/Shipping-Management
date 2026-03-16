"""
IBM i (DB2) 接続モジュール
優先順位:
  1. NODEJS_API_URL が設定されている → 既存の Node.js API 経由で取得（jt400.jar 不要）
  2. DEMO_MODE=true → サンプルデータを返す
  3. それ以外 → JayDeBeApi + jt400.jar 経由で直接接続
"""
import os
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
NODEJS_API_URL = os.getenv("NODEJS_API_URL", "").rstrip("/")  # 例: http://localhost:3001
IBMI_HOST = os.getenv("IBMI_HOST", "192.168.3.230")
IBMI_USER = os.getenv("IBMI_USER", "")
IBMI_PASSWORD = os.getenv("IBMI_PASSWORD", "")
IBMI_LIBRARY = os.getenv("IBMI_LIBRARY", "TREED")
IBMI_TABLE = os.getenv("IBMI_TABLE", "RJU1")
IBMI_DRIVER_PATH = os.getenv("IBMI_DRIVER_PATH", "/opt/jt400/jt400.jar")

QUERY = f"""
SELECT
    DENNO, TANTO, UCOD, HCOD, HNAME, HNM2,
    MNMM, MKRCD, MHNM, SURYO,
    NODAYU, NODAYS, SYKDY, HAISO,
    SYNM1, SYNM2, ADR1T, ADR2T,
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


def _date_str_to_cyymmdd(date_str: str) -> int:
    """YYYY-MM-DD → CYYMMDD 整数 (例: '2026-03-15' → 1260315)"""
    if not date_str:
        return 0
    try:
        y, m, d = date_str.split("-")
        year = int(y)
        c = 1 if year >= 2000 else 0
        return c * 1000000 + (year % 100) * 10000 + int(m) * 100 + int(d)
    except Exception:
        return 0


def fetch_from_ibmi() -> List[Dict[str, Any]]:
    """IBM i からデータを取得する（モード自動選択）"""

    # 優先1: Node.js API 経由
    if NODEJS_API_URL:
        logger.info(f"Node.js API モード: {NODEJS_API_URL}/api/orders")
        return _fetch_from_nodejs_api()

    # 優先2: デモモード
    if DEMO_MODE:
        logger.info("DEMO MODE: サンプルデータを返します")
        return _get_demo_data()

    # 優先3: 直接 JDBC 接続
    return _fetch_direct_ibmi()


def _fetch_from_nodejs_api() -> List[Dict[str, Any]]:
    """既存の Node.js IBM i ダッシュボードの /api/orders から受注残を取得する"""
    import urllib.request
    import json

    url = f"{NODEJS_API_URL}/api/orders"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode())
    except Exception as e:
        logger.error(f"Node.js API 呼び出し失敗: {e}")
        raise RuntimeError(f"Node.js API ({url}) への接続に失敗しました: {e}")

    if not body.get("success"):
        raise RuntimeError(f"Node.js API エラー: {body.get('error', '不明なエラー')}")

    orders = body.get("data", [])
    result = []
    for o in orders:
        result.append({
            "denno":      int(o.get("denno") or 0),
            "tanto":      None,
            "ucod":       int(o.get("customerCode") or 0),
            "hcod":       int(o.get("productCode") or 0),
            "hname":      (o.get("productName") or "").strip(),
            "hnm2":       None,
            "mnmm":       None,
            "mkrcd":      None,
            "mhnm":       None,
            "suryo":      int(o.get("quantity") or 0),
            "nodayu":     _date_str_to_cyymmdd(o.get("deliveryDate")),
            "nodays":     0,
            "sykdy":      0,
            "haiso":      None,
            "synm1":      None,
            "synm2":      None,
            "adr1t":      None,
            "adr2t":      None,
            "utno1":      None,
            "juchu":      "1",
            "uriag":      "0",
            "order_flg":  "0",
            "slcrt":      0,
            "dtadd":      None,
        })

    logger.info(f"Node.js API から {len(result)} 件取得しました")
    return result


def _fetch_direct_ibmi() -> List[Dict[str, Any]]:
    """JayDeBeApi + jt400.jar で IBM i に直接接続"""
    try:
        import jaydebeapi
        conn = jaydebeapi.connect(
            "com.ibm.as400.access.AS400JDBCDriver",
            f"jdbc:as400://{IBMI_HOST}",
            [IBMI_USER, IBMI_PASSWORD],
            IBMI_DRIVER_PATH,
        )
        cursor = conn.cursor()
        cursor.execute(QUERY)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        result = []
        for row in rows:
            record = dict(zip(COLUMNS, row))
            for key in ["denno", "ucod", "hcod", "suryo", "nodayu", "nodays", "sykdy", "slcrt"]:
                if record.get(key) is not None:
                    try:
                        record[key] = int(record[key])
                    except (ValueError, TypeError):
                        record[key] = 0
            for key in COLUMNS:
                if isinstance(record.get(key), str):
                    record[key] = record[key].strip()
            result.append(record)

        logger.info(f"IBM i (直接接続) から {len(result)} 件取得しました")
        return result

    except ImportError:
        logger.error("JayDeBeApi がインストールされていません")
        raise RuntimeError("JayDeBeApi not installed。NODEJS_API_URL か DEMO_MODE=true を設定してください")
    except Exception as e:
        logger.error(f"IBM i 接続エラー: {e}")
        raise


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
