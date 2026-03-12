from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from ..database import get_db_conn
from ..ibmi import ibmi_date_to_str

router = APIRouter()


@router.get("/shipments/{denno}/label", response_class=HTMLResponse)
def generate_label(denno: int):
    """荷札HTML生成（ブラウザで印刷）"""
    conn = get_db_conn()
    try:
        row = conn.execute(
            "SELECT * FROM shipments WHERE denno = ?", (denno,)
        ).fetchone()
    finally:
        conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="伝票番号が見つかりません")

    d = dict(row)
    nodayu_str = ibmi_date_to_str(d.get("nodayu")) or "-"
    synm = f"{d.get('synm1', '') or ''} {d.get('synm2', '') or ''}".strip()
    adr = f"{d.get('adr1t', '') or ''} {d.get('adr2t', '') or ''}".strip()

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>荷札 - {d['denno']}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'MS Gothic', 'Hiragino Kaku Gothic ProN', sans-serif; }}
    .label {{
      width: 148mm; height: 105mm; /* A6横 */
      border: 2px solid #000;
      padding: 6mm;
      display: flex;
      flex-direction: column;
      gap: 3mm;
    }}
    .label-title {{
      text-align: center;
      font-size: 18pt;
      font-weight: bold;
      border-bottom: 1px solid #000;
      padding-bottom: 2mm;
    }}
    .label-body {{ flex: 1; display: flex; flex-direction: column; gap: 2mm; }}
    .field {{ display: flex; gap: 4mm; font-size: 9pt; }}
    .field-label {{ min-width: 22mm; font-weight: bold; color: #444; }}
    .field-value {{ flex: 1; }}
    .large {{ font-size: 13pt; font-weight: bold; }}
    .denno-box {{
      border: 1.5px solid #000;
      padding: 1mm 3mm;
      text-align: center;
      font-size: 14pt;
      font-weight: bold;
      letter-spacing: 2px;
    }}
    @media print {{
      @page {{ size: A6 landscape; margin: 0; }}
      body {{ print-color-adjust: exact; }}
    }}
  </style>
</head>
<body>
  <div class="label">
    <div class="label-title">荷　札</div>
    <div class="label-body">
      <div class="field">
        <span class="field-label">伝票番号</span>
        <span class="field-value denno-box">{d.get('denno', '')}</span>
      </div>
      <div class="field">
        <span class="field-label">出荷先</span>
        <span class="field-value large">{synm}</span>
      </div>
      <div class="field">
        <span class="field-label">住所</span>
        <span class="field-value">{adr}</span>
      </div>
      <div class="field">
        <span class="field-label">品名</span>
        <span class="field-value large">{d.get('hname', '') or ''}</span>
      </div>
      <div class="field">
        <span class="field-label">型式</span>
        <span class="field-value">{d.get('hnm2', '') or ''}</span>
      </div>
      <div class="field">
        <span class="field-label">数量</span>
        <span class="field-value large">{d.get('suryo', '') or ''}</span>
      </div>
      <div class="field">
        <span class="field-label">納期</span>
        <span class="field-value">{nodayu_str}</span>
      </div>
      <div class="field">
        <span class="field-label">得意先注番</span>
        <span class="field-value">{d.get('utno1', '') or ''}</span>
      </div>
      {'<div class="field"><span class="field-label">備考</span><span class="field-value">' + str(d.get('dtadd') or '') + '</span></div>' if d.get('dtadd') else ''}
    </div>
  </div>
  <script>window.onload = () => window.print();</script>
</body>
</html>"""
    return HTMLResponse(content=html)
