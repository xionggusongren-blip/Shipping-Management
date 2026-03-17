"""荷札PDF生成 API"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from io import BytesIO

from database import get_db, ShipmentCache, ShipmentStatus
from models import ibmi_date_to_str
from auth import get_current_user, User

router = APIRouter()

HAISO_NAMES = {
    "YAMTO": "ヤマト運輸",
    "SAGAWA": "佐川急便",
    "FUKUTU": "福山通運",
    "NIPPON": "日本郵便",
    "SEINO": "西濃運輸",
}


def _generate_label_pdf(cache: ShipmentCache, status_rec) -> bytes:
    """荷札PDFを生成する（ReportLab使用）"""
    try:
        from reportlab.lib.pagesizes import A6
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    except ImportError:
        raise RuntimeError("reportlab がインストールされていません")

    buffer = BytesIO()
    # A6サイズ（148mm x 105mm）横向き
    page_width, page_height = 148 * mm, 105 * mm
    c = canvas.Canvas(buffer, pagesize=(page_width, page_height))

    # 日本語フォント登録
    try:
        pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))
        font_name = "HeiseiMin-W3"
    except Exception:
        font_name = "Helvetica"

    margin = 5 * mm

    # 枠線
    c.setLineWidth(1.5)
    c.rect(margin, margin, page_width - 2 * margin, page_height - 2 * margin)

    # タイトル行
    c.setFont(font_name, 12)
    c.drawString(margin + 3 * mm, page_height - margin - 10 * mm, "荷　札")

    # 出荷先
    c.setFont(font_name, 14)
    synm1 = (cache.synm1 or "").strip()
    synm2 = (cache.synm2 or "").strip()
    c.drawString(margin + 3 * mm, page_height - margin - 22 * mm, synm1)
    if synm2:
        c.setFont(font_name, 11)
        c.drawString(margin + 3 * mm, page_height - margin - 31 * mm, synm2)

    # 住所
    c.setFont(font_name, 9)
    adr1 = (cache.adr1t or "").strip()
    adr2 = (cache.adr2t or "").strip()
    c.drawString(margin + 3 * mm, page_height - margin - 40 * mm, adr1)
    if adr2:
        c.drawString(margin + 3 * mm, page_height - margin - 47 * mm, adr2)

    # 区切り線
    c.setLineWidth(0.5)
    y_sep = page_height - margin - 52 * mm
    c.line(margin, y_sep, page_width - margin, y_sep)

    # 品名・数量
    c.setFont(font_name, 10)
    hname = (cache.hname or "").strip()
    hnm2 = (cache.hnm2 or "").strip()
    c.drawString(margin + 3 * mm, y_sep - 8 * mm, f"品名: {hname}")
    if hnm2:
        c.drawString(margin + 3 * mm, y_sep - 15 * mm, f"型式: {hnm2}")
    c.drawString(margin + 3 * mm, y_sep - 22 * mm, f"数量: {cache.suryo or 0}")

    # 伝票番号・納期・配送
    c.setFont(font_name, 9)
    nodayu_str = ibmi_date_to_str(cache.nodayu) or "-"
    haiso_name = HAISO_NAMES.get((cache.haiso or "").strip(), (cache.haiso or "").strip())
    c.drawString(margin + 3 * mm, y_sep - 32 * mm, f"伝票番号: {cache.denno}")
    c.drawString(margin + 60 * mm, y_sep - 32 * mm, f"納期: {nodayu_str}")
    c.drawString(margin + 3 * mm, y_sep - 39 * mm, f"配送: {haiso_name}")

    # 備考
    dtadd = (cache.dtadd or "").strip()
    if dtadd:
        c.setFont(font_name, 9)
        c.drawString(margin + 60 * mm, y_sep - 39 * mm, f"備考: {dtadd}")

    # 得意先注番（バーコード代替）
    utno1 = (cache.utno1 or "").strip()
    if utno1:
        c.setFont(font_name, 8)
        c.drawString(margin + 3 * mm, margin + 5 * mm, f"注番: {utno1}")

    c.save()
    buffer.seek(0)
    return buffer.read()


def _generate_meisai_pdf(cache: ShipmentCache, status_rec) -> bytes:
    """出荷明細書PDF（A4縦）を生成する"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    except ImportError:
        raise RuntimeError("reportlab がインストールされていません")

    buffer = BytesIO()
    page_width, page_height = A4  # 210mm × 297mm
    c = canvas.Canvas(buffer, pagesize=A4)

    try:
        pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))
        fn = "HeiseiMin-W3"
    except Exception:
        fn = "Helvetica"

    from datetime import datetime
    now_str = datetime.now().strftime("%Y/%m/%d %H:%M")
    margin = 15 * mm

    # 外枠
    c.setLineWidth(1.5)
    c.rect(margin, margin, page_width - 2 * margin, page_height - 2 * margin)

    y = page_height - margin - 12 * mm

    # タイトル
    c.setFont(fn, 18)
    c.drawCentredString(page_width / 2, y, "出荷明細書")
    y -= 8 * mm
    c.setFont(fn, 8)
    c.drawRightString(page_width - margin, y, f"印刷日時: {now_str}")
    y -= 6 * mm

    # 区切り線
    c.setLineWidth(0.8)
    c.line(margin, y, page_width - margin, y)
    y -= 8 * mm

    status = (status_rec.status if status_rec else "未処理")
    utno1 = (cache.utno1 or "").strip()
    haiso_name = HAISO_NAMES.get((cache.haiso or "").strip(), (cache.haiso or "").strip())
    nodayu_str = ibmi_date_to_str(cache.nodayu) or "-"
    nodays_str = ibmi_date_to_str(cache.nodays) if hasattr(cache, "nodays") and cache.nodays else "-"

    # 行ヘルパー
    def row(label, value, y_pos, label_x=margin + 3 * mm, val_x=margin + 50 * mm, font_size=11):
        c.setFont(fn, 9)
        c.setFillColorRGB(0.4, 0.4, 0.4)
        c.drawString(label_x, y_pos, label)
        c.setFont(fn, font_size)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(val_x, y_pos, str(value) if value else "-")
        return y_pos - 9 * mm

    # ===== セクション1: 送り状・伝票 =====
    c.setFont(fn, 9)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawString(margin + 3 * mm, y, "■ 送り状・伝票情報")
    c.setFillColorRGB(0, 0, 0)
    y -= 6 * mm

    y = row("送り状番号", utno1 or "-", y, font_size=13)
    y = row("伝票番号", str(cache.denno), y)
    y = row("ステータス", status, y)
    y -= 2 * mm
    c.setLineWidth(0.3)
    c.line(margin + 3 * mm, y, page_width - margin - 3 * mm, y)
    y -= 6 * mm

    # ===== セクション2: 出荷先 =====
    c.setFont(fn, 9)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawString(margin + 3 * mm, y, "■ 出荷先")
    c.setFillColorRGB(0, 0, 0)
    y -= 6 * mm

    synm1 = (cache.synm1 or "").strip()
    synm2 = (cache.synm2 or "").strip()
    adr1 = (cache.adr1t or "").strip()
    adr2 = (cache.adr2t or "").strip()
    y = row("会社名", synm1, y, font_size=12)
    if synm2:
        y = row("部署名", synm2, y)
    y = row("住所1", adr1, y)
    if adr2:
        y = row("住所2", adr2, y)
    y -= 2 * mm
    c.line(margin + 3 * mm, y, page_width - margin - 3 * mm, y)
    y -= 6 * mm

    # ===== セクション3: 品目 =====
    c.setFont(fn, 9)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawString(margin + 3 * mm, y, "■ 品目情報")
    c.setFillColorRGB(0, 0, 0)
    y -= 6 * mm

    hname = (cache.hname or "").strip()
    hnm2 = (cache.hnm2 or "").strip()
    mnmm = (cache.mnmm or "").strip()
    y = row("品名", hname, y, font_size=12)
    if hnm2:
        y = row("型式", hnm2, y)
    if mnmm:
        y = row("メーカー", mnmm, y)
    y = row("数量", str(cache.suryo or 0), y)
    y -= 2 * mm
    c.line(margin + 3 * mm, y, page_width - margin - 3 * mm, y)
    y -= 6 * mm

    # ===== セクション4: 配送・納期 =====
    c.setFont(fn, 9)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawString(margin + 3 * mm, y, "■ 配送・納期")
    c.setFillColorRGB(0, 0, 0)
    y -= 6 * mm

    y = row("配送方法", haiso_name, y)
    y = row("納期", nodayu_str, y)
    y = row("担当者", (cache.tanto or "").strip(), y)

    dtadd = (cache.dtadd or "").strip()
    if dtadd:
        y -= 2 * mm
        c.line(margin + 3 * mm, y, page_width - margin - 3 * mm, y)
        y -= 6 * mm
        c.setFont(fn, 9)
        c.setFillColorRGB(0.2, 0.2, 0.2)
        c.drawString(margin + 3 * mm, y, "■ 備考")
        c.setFillColorRGB(0, 0, 0)
        y -= 6 * mm
        y = row("備考", dtadd, y)

    c.save()
    buffer.seek(0)
    return buffer.read()



@router.get("/shipments/{denno}/meisai")
def get_meisai(
    denno: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """出荷明細書PDFを生成してダウンロードする"""
    cache = db.query(ShipmentCache).filter(ShipmentCache.denno == denno).first()
    if not cache:
        raise HTTPException(status_code=404, detail="荷物が見つかりません")
    status_rec = db.query(ShipmentStatus).filter(ShipmentStatus.denno == denno).first()
    try:
        pdf_bytes = _generate_meisai_pdf(cache, status_rec)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=meisai_{denno}.pdf"},
    )


@router.get("/shipments/{denno}/label")
def get_label(
    denno: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """荷札PDFを生成してダウンロードする"""
    cache = db.query(ShipmentCache).filter(ShipmentCache.denno == denno).first()
    if not cache:
        raise HTTPException(status_code=404, detail="荷物が見つかりません")

    status_rec = db.query(ShipmentStatus).filter(ShipmentStatus.denno == denno).first()

    try:
        pdf_bytes = _generate_label_pdf(cache, status_rec)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=label_{denno}.pdf"},
    )
