import os
import sys
import tempfile
import uuid
from dataclasses import dataclass
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from .barcode import build_scan_payload, render_barcode_png


@dataclass
class PrintRow:
    art_num: str
    cartons: int
    qty_per_carton: int
    qty: int

    @property
    def barcode_payload(self) -> str:
        return build_scan_payload(self.art_num, self.qty)


def build_pdf(rows: list[PrintRow]) -> bytes:
    buf = BytesIO()
    page_w, page_h = A4
    margin = 15 * mm
    c = canvas.Canvas(buf, pagesize=A4)

    row_height = 28 * mm
    header_height = 22 * mm
    title_height = 18 * mm
    usable_h = page_h - 2 * margin - title_height - header_height
    rows_per_page = max(1, int(usable_h // row_height))

    col_art = margin
    col_cartons = margin + 42 * mm
    col_qty = margin + 62 * mm
    col_barcode = margin + 82 * mm
    barcode_w = page_w - col_barcode - margin
    barcode_h = 18 * mm

    def draw_title():
        c.setFillColor(colors.HexColor("#326633"))
        c.setFont("Helvetica-Bold", 16)
        c.drawString(margin, page_h - margin - 6 * mm, "WH Pallet Printer")
        c.setStrokeColor(colors.HexColor("#326633"))
        c.setLineWidth(1.5)
        c.line(margin, page_h - margin - 10 * mm, page_w - margin, page_h - margin - 10 * mm)

    def draw_table_header(y: float):
        c.setFillColor(colors.HexColor("#f3faf3"))
        c.rect(margin, y - header_height + 4 * mm, page_w - 2 * margin, header_height, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#326633"))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(col_art + 2 * mm, y, "Art Num")
        c.drawString(col_cartons, y, "Cartons")
        c.drawString(col_qty, y, "Qty")
        c.drawString(col_barcode, y, "Barcode")
        c.setStrokeColor(colors.HexColor("#cbe7cb"))
        c.line(margin, y - 4 * mm, page_w - margin, y - 4 * mm)

    draw_title()
    y = page_h - margin - title_height - header_height
    draw_table_header(y)
    y -= 8 * mm

    for idx, row in enumerate(rows):
        if idx > 0 and idx % rows_per_page == 0:
            c.showPage()
            draw_title()
            y = page_h - margin - title_height - header_height
            draw_table_header(y)
            y -= 8 * mm

        c.setFillColor(colors.black)
        c.setFont("Helvetica", 10)
        c.drawString(col_art + 2 * mm, y, row.art_num)
        c.drawString(col_cartons, y, str(row.cartons))
        c.drawString(col_qty, y, str(row.qty))

        png = render_barcode_png(row.barcode_payload)
        img_y = y - barcode_h + 4 * mm
        c.drawImage(ImageReader(BytesIO(png)), col_barcode, img_y, width=barcode_w, height=barcode_h)
        c.setFont("Helvetica", 7)
        c.setFillColor(colors.HexColor("#5a7a5a"))
        c.drawString(col_barcode, img_y - 4 * mm, f"{row.art_num} / Qty {row.qty}")

        c.setStrokeColor(colors.HexColor("#e2e8e2"))
        c.line(margin, y - row_height + 6 * mm, page_w - margin, y - row_height + 6 * mm)
        y -= row_height

    c.save()
    return buf.getvalue()


def print_pdf(pdf_bytes: bytes) -> str:
    job_id = str(uuid.uuid4())[:8]
    tmp_dir = tempfile.gettempdir()
    pdf_path = os.path.join(tmp_dir, f"wh_pallet_print_{job_id}.pdf")
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    if sys.platform == "win32":
        os.startfile(pdf_path, "print")
    else:
        # Dev fallback on macOS/Linux: open file instead of printing
        if sys.platform == "darwin":
            os.system(f'open "{pdf_path}"')
        else:
            os.system(f'xdg-open "{pdf_path}"')

    return pdf_path
