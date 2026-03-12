import logging
from typing import List, Dict, Any, Optional
from .config import settings

logger = logging.getLogger(__name__)

# 要件定義書 3.2 基本SQLクエリ
BASE_SQL = """
SELECT
    DENNO, TANTO, UCOD, HCOD, HNAME, HNM2,
    MNMM, MKRCD, MHNM, SURYO,
    NODAYU, NODAYS, SYKDY, HAISO,
    SYNM1, SYNM2, ADR1T, ADR2T,
    UTNO1, JUCHU, URIAG, "ORDER",
    SLCRT, DTADD
FROM TREED.RJU1
WHERE RJU1D <> '1'
  AND URIAG <> '1'
ORDER BY NODAYU, DENNO
"""


def ibmi_date_to_str(val) -> Optional[str]:
    """CYYMMDD形式 (DECIMAL 7) を YYYY/MM/DD に変換（要件定義書 3.4）"""
    if not val or int(val) == 0:
        return None
    s = str(int(val)).zfill(7)
    c, yy, mm, dd = s[0], s[1:3], s[3:5], s[5:7]
    year = 1900 + int(c) * 100 + int(yy)
    return f"{year}/{mm}/{dd}"


def fetch_rju1_data() -> List[Dict[str, Any]]:
    """IBM i RJU1 からJDBC経由でデータ取得。接続不可時はモックデータを返す。"""
    try:
        import jaydebeapi
        conn = jaydebeapi.connect(
            "com.ibm.as400.access.AS400JDBCDriver",
            f"jdbc:as400://{settings.IBMI_HOST}",
            [settings.IBMI_USER, settings.IBMI_PASSWORD],
            settings.JT400_JAR_PATH,
        )
        cursor = conn.cursor()
        cursor.execute(BASE_SQL)
        columns = [desc[0].lower() for desc in cursor.description]
        # ORDER は予約語のためリネーム
        columns = ["order_col" if c == "order" else c for c in columns]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        logger.info(f"IBM i RJU1 から {len(rows)} 件取得")
        return rows
    except ImportError:
        logger.warning("JayDeBeApi が利用不可 → モックデータを使用")
        return _mock_data()
    except Exception as e:
        logger.error(f"IBM i 接続エラー: {e}")
        raise


def _mock_data() -> List[Dict[str, Any]]:
    """開発・テスト用モックデータ"""
    return [
        {
            "denno": 1234567, "tanto": "T001", "ucod": 100001,
            "hcod": 2000001, "hname": "サンプル製品A", "hnm2": "TypeA-100",
            "mnmm": "サンプルメーカー", "mkrcd": "MK001", "mhnm": "PART-001",
            "suryo": 5.0, "nodayu": 1260315, "nodays": 1260315, "sykdy": 0,
            "haiso": "H001", "synm1": "株式会社テスト得意先", "synm2": "営業部",
            "adr1t": "東京都渋谷区", "adr2t": "1-1-1",
            "utno1": "UTN-001", "juchu": "0", "uriag": "0",
            "order_col": "0", "slcrt": 1001, "dtadd": "備考なし",
        },
        {
            "denno": 1234568, "tanto": "T002", "ucod": 100002,
            "hcod": 2000002, "hname": "サンプル製品B", "hnm2": "TypeB-200",
            "mnmm": "別メーカー", "mkrcd": "MK002", "mhnm": "PART-002",
            "suryo": 10.0, "nodayu": 1260320, "nodays": 1260320, "sykdy": 1260312,
            "haiso": "H002", "synm1": "株式会社サンプル商事", "synm2": "購買部",
            "adr1t": "大阪府大阪市中央区", "adr2t": "2-2-2",
            "utno1": "UTN-002", "juchu": "1", "uriag": "0",
            "order_col": "1", "slcrt": 1002, "dtadd": "急ぎ",
        },
        {
            "denno": 1234569, "tanto": "T001", "ucod": 100003,
            "hcod": 2000003, "hname": "サンプル製品C", "hnm2": "TypeC-300",
            "mnmm": "サンプルメーカー", "mkrcd": "MK001", "mhnm": "PART-003",
            "suryo": 3.0, "nodayu": 1260310, "nodays": 1260310, "sykdy": 0,
            "haiso": "H001", "synm1": "テスト物産株式会社", "synm2": "",
            "adr1t": "愛知県名古屋市", "adr2t": "3-3-3",
            "utno1": "UTN-003", "juchu": "0", "uriag": "0",
            "order_col": "0", "slcrt": 1001, "dtadd": "",
        },
        {
            "denno": 1234570, "tanto": "T003", "ucod": 100004,
            "hcod": 2000004, "hname": "サンプル製品D", "hnm2": "TypeD-400",
            "mnmm": "第三メーカー", "mkrcd": "MK003", "mhnm": "PART-004",
            "suryo": 20.0, "nodayu": 1260308, "nodays": 1260308, "sykdy": 0,
            "haiso": "H003", "synm1": "北海道物流株式会社", "synm2": "",
            "adr1t": "北海道札幌市北区", "adr2t": "4-4-4",
            "utno1": "UTN-004", "juchu": "0", "uriag": "0",
            "order_col": "0", "slcrt": 1003, "dtadd": "注意：割れ物",
        },
    ]
