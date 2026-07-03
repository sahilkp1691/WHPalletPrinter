import os
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass
from io import BytesIO
from typing import Literal

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from ..models import (
    PRINT_FORMAT_A4,
    PRINT_FORMAT_LABEL_10X15,
    PRINT_ORIENTATION_LANDSCAPE,
    PRINT_ORIENTATION_PORTRAIT,
)
from .code128 import build_scan_payload, render_barcode_for_print

PrintFormat = Literal["a4", "label_10x15"]
PrintOrientation = Literal["portrait", "landscape"]

LABEL_SHORT_MM = 100
LABEL_LONG_MM = 150
LABEL_MARGIN_MM = 8


@dataclass
class PrintRow:
    art_num: str
    cartons: int
    qty_per_carton: int
    qty: int
    pallet_num: str = ""

    @property
    def barcode_payload(self) -> str:
        return build_scan_payload(self.art_num, self.qty)


def _page_size(
    print_format: PrintFormat,
    orientation: PrintOrientation,
) -> tuple[float, float]:
    if print_format == PRINT_FORMAT_LABEL_10X15:
        # Match physical 10×15 cm label (portrait feed).
        return LABEL_SHORT_MM * mm, LABEL_LONG_MM * mm

    if orientation == PRINT_ORIENTATION_LANDSCAPE:
        return landscape(A4)
    return A4


def _mm_to_pt(size_mm: float) -> float:
    return size_mm * 72 / 25.4


def _draw_barcode_bitmap(
    c: canvas.Canvas,
    payload: str,
    center_x: float,
    y_bottom: float,
    max_width: float,
    bar_height: float,
    dpi: int = 300,
) -> None:
    png, w_pt, h_pt = render_barcode_for_print(payload, max_width, bar_height, dpi=dpi)
    x = center_x - w_pt / 2
    c.drawImage(ImageReader(BytesIO(png)), x, y_bottom, w_pt, h_pt, mask="auto")


def _fit_font_pt(
    c: canvas.Canvas,
    text: str,
    font_name: str,
    start_mm: float,
    min_mm: float,
    max_width: float,
) -> float:
    for size_mm in range(int(start_mm * 10), int(min_mm * 10) - 1, -2):
        pt = _mm_to_pt(size_mm / 10)
        if c.stringWidth(text, font_name, pt) <= max_width:
            return pt
    return _mm_to_pt(min_mm)


def _draw_label_page(c: canvas.Canvas, row: PrintRow, page_w: float, page_h: float) -> None:
    margin = LABEL_MARGIN_MM * mm
    inner_w = page_w - 2 * margin
    inner_h = page_h - 2 * margin
    x_center = page_w / 2

    # Target warehouse-readable sizes, then scale everything to fit the safe inner box.
    pallet_mm = 11.0
    art_mm = 20.0
    line_mm = 13.0
    sub_mm = 10.0
    line_gap_mm = 2.5
    text_barcode_gap_mm = 4.0
    min_barcode_mm = 28.0

    text_h_mm = pallet_mm + art_mm + line_mm * 2 + sub_mm + line_gap_mm * 4 + text_barcode_gap_mm
    barcode_mm = max(min_barcode_mm, inner_h / mm * 0.46 - text_h_mm * 0.15)
    total_mm = text_h_mm + barcode_mm
    if total_mm > inner_h / mm:
        shrink = (inner_h / mm) / total_mm
        pallet_mm *= shrink
        art_mm *= shrink
        line_mm *= shrink
        sub_mm *= shrink
        line_gap_mm *= shrink
        text_barcode_gap_mm *= shrink
        barcode_mm = max(min_barcode_mm * shrink, inner_h / mm - text_h_mm * shrink)

    pallet_pt = _mm_to_pt(pallet_mm)
    art_pt = _fit_font_pt(c, row.art_num, "Helvetica-Bold", art_mm, 10, inner_w)
    detail_pt = _mm_to_pt(line_mm)
    sub_pt = _mm_to_pt(sub_mm)
    line_gap = line_gap_mm * mm
    gap_text_barcode = text_barcode_gap_mm * mm
    barcode_h = barcode_mm * mm

    y = page_h - margin

    c.setFillColor(colors.black)
    if row.pallet_num:
        c.setFont("Helvetica-Bold", pallet_pt)
        y -= pallet_pt * 0.82
        c.drawCentredString(x_center, y, f"PALLET: {row.pallet_num}")
        y -= line_gap * 0.5

    c.setFont("Helvetica-Bold", art_pt)
    y -= art_pt * 0.82
    c.drawCentredString(x_center, y, row.art_num)
    y -= line_gap

    c.setFont("Helvetica-Bold", detail_pt)
    y -= detail_pt * 0.82
    c.drawCentredString(x_center, y, f"QTY: {row.qty}")
    y -= line_gap * 0.75

    y -= detail_pt * 0.82
    c.drawCentredString(x_center, y, f"CTNS: {row.cartons}")
    y -= line_gap * 0.65

    c.setFont("Helvetica-Bold", sub_pt)
    y -= sub_pt * 0.82
    c.drawCentredString(x_center, y, f"{row.qty_per_carton} / CTN")
    y -= gap_text_barcode

    barcode_bottom = margin
    barcode_h = min(barcode_h, y - barcode_bottom)
    _draw_barcode_bitmap(
        c,
        row.barcode_payload,
        x_center,
        barcode_bottom,
        inner_w,
        barcode_h,
    )


def _build_label_pdf(rows: list[PrintRow], pagesize: tuple[float, float]) -> bytes:
    buf = BytesIO()
    page_w, page_h = pagesize
    c = canvas.Canvas(buf, pagesize=pagesize)

    for idx, row in enumerate(rows):
        if idx > 0:
            c.showPage()
        _draw_label_page(c, row, page_w, page_h)

    c.save()
    return buf.getvalue()


def _build_a4_pdf(rows: list[PrintRow], pagesize: tuple[float, float]) -> bytes:
    buf = BytesIO()
    page_w, page_h = pagesize
    is_landscape = page_w > page_h
    margin = 15 * mm if is_landscape else 12 * mm
    cell_pad = 4 * mm
    c = canvas.Canvas(buf, pagesize=pagesize)

    row_height = 34 * mm if is_landscape else 32 * mm
    header_text_gap = 5 * mm
    header_line_gap = 5 * mm
    header_content_gap = 8 * mm
    row_text_offset = 10 * mm
    row_divider_pad = 3 * mm
    header_block = header_text_gap + header_line_gap + header_content_gap + 6 * mm
    usable_h = page_h - 2 * margin - header_block
    rows_per_page = max(1, int(usable_h // row_height))

    table_w = page_w - 2 * margin
    col_art = margin + cell_pad
    col_cartons = margin + table_w * 0.20 + cell_pad
    col_qty = margin + table_w * 0.36 + cell_pad
    col_barcode = margin + table_w * 0.50 + cell_pad
    barcode_h = 22 * mm if is_landscape else 20 * mm
    font_header = 16 if is_landscape else 15
    font_data = 14 if is_landscape else 13

    pallet_num = rows[0].pallet_num if rows else ""

    def draw_table_header(row_top: float) -> float:
        """Draw column titles and divider; return top y of first data row."""
        text_y = row_top - header_text_gap
        c.setFillColor(colors.black)
        if pallet_num:
            c.setFont("Helvetica-Bold", font_header)
            c.drawString(margin, text_y + 6 * mm, f"Pallet: {pallet_num}")
            text_y -= 6 * mm
        c.setFont("Helvetica-Bold", font_header)
        c.drawString(col_art, text_y, "Art Num")
        c.drawString(col_cartons, text_y, "Cartons")
        c.drawString(col_qty, text_y, "Qty")
        c.drawString(col_barcode, text_y, "Barcode")
        line_y = text_y - header_line_gap
        c.setLineWidth(1.2)
        c.line(margin, line_y, page_w - margin, line_y)
        return line_y - header_content_gap

    row_top = page_h - margin
    row_top = draw_table_header(row_top)

    for idx, row in enumerate(rows):
        if idx > 0 and idx % rows_per_page == 0:
            c.showPage()
            row_top = page_h - margin
            row_top = draw_table_header(row_top)

        row_bottom = row_top - row_height
        text_y = row_top - row_text_offset

        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", font_data)
        c.drawString(col_art, text_y, row.art_num)
        c.drawString(col_cartons, text_y, str(row.cartons))
        c.drawString(col_qty, text_y, str(row.qty))

        bc_max_w = page_w - col_barcode - margin - cell_pad
        barcode_y = row_bottom + row_divider_pad + 2 * mm
        _draw_barcode_bitmap(
            c,
            row.barcode_payload,
            col_barcode + bc_max_w / 2,
            barcode_y,
            bc_max_w,
            barcode_h,
        )

        divider_y = row_bottom + row_divider_pad
        c.setLineWidth(0.6)
        c.line(margin, divider_y, page_w - margin, divider_y)
        row_top = row_bottom

    c.save()
    return buf.getvalue()


def build_pdf(
    rows: list[PrintRow],
    print_format: PrintFormat = PRINT_FORMAT_A4,
    orientation: PrintOrientation = PRINT_ORIENTATION_PORTRAIT,
) -> bytes:
    pagesize = _page_size(print_format, orientation)
    if print_format == PRINT_FORMAT_LABEL_10X15:
        return _build_label_pdf(rows, pagesize)
    return _build_a4_pdf(rows, pagesize)


class PrintError(Exception):
    pass


def _program_files_dirs() -> list[str]:
    dirs = []
    for key in ("ProgramFiles", "ProgramFiles(x86)", "LocalAppData"):
        value = os.environ.get(key)
        if value:
            dirs.append(value)
    return dirs


def _first_existing(paths: list[str]) -> str | None:
    for path in paths:
        if path and os.path.isfile(path):
            return path
    return None


def _is_label_page(width_pt: float, height_pt: float) -> bool:
    short = min(width_pt, height_pt)
    long = max(width_pt, height_pt)
    return short <= 300 and long <= 450


def _create_printer_hdc(printer: str, landscape: bool | None, label_page: bool = False):
    import win32con
    import win32gui
    import win32print
    import win32ui

    hdc = win32ui.CreateDC()
    hdc.CreatePrinterDC(printer)

    handle = win32print.OpenPrinter(printer)
    try:
        info = win32print.GetPrinter(handle, 2)
        devmode = info["pDevMode"]
        if devmode is not None:
            if label_page:
                # Zebra/driver default is often ~102x64 mm; force true 10x15 cm media.
                devmode.PaperSize = win32con.DMPAPER_USER
                devmode.PaperWidth = LABEL_SHORT_MM * 10
                devmode.PaperLength = LABEL_LONG_MM * 10
                devmode.Orientation = win32con.DMORIENT_PORTRAIT
            elif landscape is not None:
                devmode.Orientation = (
                    win32con.DMORIENT_LANDSCAPE if landscape else win32con.DMORIENT_PORTRAIT
                )
            win32gui.ResetDC(hdc.GetHandleOutput(), devmode)
    finally:
        win32print.ClosePrinter(handle)
    return hdc


def _pdf_page_kind(pdf_path: str) -> tuple[bool, bool]:
    import fitz

    doc = fitz.open(pdf_path)
    try:
        first = doc[0].rect
        label_page = _is_label_page(first.width, first.height)
        page_landscape = first.width > first.height
        return label_page, page_landscape
    finally:
        doc.close()


def _print_via_win32(pdf_path: str, printer: str | None, label_page: bool) -> None:
    import fitz
    import win32print
    from PIL import Image, ImageWin

    target = printer or win32print.GetDefaultPrinter()
    doc = fitz.open(pdf_path)
    first = doc[0].rect
    page_landscape = first.width > first.height
    printer_landscape = False if label_page else page_landscape

    hdc = _create_printer_hdc(target, printer_landscape, label_page=label_page)

    printable_w = hdc.GetDeviceCaps(8)   # HORZRES
    printable_h = hdc.GetDeviceCaps(10)  # VERTRES
    offset_x = hdc.GetDeviceCaps(112)    # PHYSOFFSETX
    offset_y = hdc.GetDeviceCaps(113)    # PHYSOFFSETY
    log_pixels_x = hdc.GetDeviceCaps(88)  # LOGPIXELSX
    log_pixels_y = hdc.GetDeviceCaps(90)  # LOGPIXELSY
    render_dpi = max(300 if label_page else 203, log_pixels_x, log_pixels_y)
    resample = Image.Resampling.NEAREST if label_page else Image.Resampling.LANCZOS
    inset = 0.96 if label_page else 1.0

    hdc.StartDoc(os.path.basename(pdf_path))
    try:
        for page in doc:
            pix = page.get_pixmap(dpi=render_dpi)
            mode = "RGBA" if pix.alpha else "RGB"
            img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
            if mode == "RGBA":
                img = img.convert("RGB")

            max_w = int(printable_w * inset)
            max_h = int(printable_h * inset)
            scale = min(max_w / pix.width, max_h / pix.height)
            if label_page:
                scale = min(1.0, scale)
            draw_w = int(pix.width * scale)
            draw_h = int(pix.height * scale)

            off_x = offset_x + max(0, (printable_w - draw_w) // 2)
            off_y = offset_y + max(0, (printable_h - draw_h) // 2)

            if pix.width != draw_w or pix.height != draw_h:
                img = img.resize((draw_w, draw_h), resample)

            hdc.StartPage()
            dib = ImageWin.Dib(img)
            dib.draw(
                hdc.GetHandleOutput(),
                (off_x, off_y, off_x + draw_w, off_y + draw_h),
            )
            hdc.EndPage()
    finally:
        hdc.EndDoc()
        hdc.DeleteDC()
        doc.close()


def _bundled_sumatra_paths() -> list[str]:
    candidates: list[str] = []
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        candidates.extend(
            [
                os.path.join(exe_dir, "SumatraPDF.exe"),
                os.path.join(exe_dir, "tools", "SumatraPDF.exe"),
            ]
        )
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    candidates.append(os.path.join(repo_root, "tools", "SumatraPDF.exe"))
    return [path for path in candidates if os.path.isfile(path)]


def _pdf_viewer_commands(pdf_path: str, printer: str | None) -> list[list[str]]:
    roots = _program_files_dirs()
    acrobat = _first_existing(
        [
            os.path.join(root, "Adobe", "Acrobat DC", "Acrobat", "Acrobat.exe")
            for root in roots
        ]
        + [
            os.path.join(root, "Adobe", "Acrobat Reader DC", "Reader", "AcroRd32.exe")
            for root in roots
        ]
        + [
            os.path.join(root, "Adobe", "Acrobat Reader", "Reader", "AcroRd32.exe")
            for root in roots
        ]
    )
    foxit = _first_existing(
        [
            os.path.join(root, "Foxit Software", "Foxit PDF Reader", "FoxitPDFReader.exe")
            for root in roots
        ]
        + [
            os.path.join(root, "Foxit Software", "Foxit Reader", "FoxitReader.exe")
            for root in roots
        ]
    )
    sumatra = _first_existing(
        _bundled_sumatra_paths()
        + [os.path.join(root, "SumatraPDF", "SumatraPDF.exe") for root in roots]
        + [os.path.join(root, "Programs", "SumatraPDF", "SumatraPDF.exe") for root in roots]
    )

    commands: list[list[str]] = []
    if acrobat:
        args = [acrobat, "/t", pdf_path]
        if printer:
            args.append(printer)
        commands.append(args)

    if foxit:
        args = [foxit, "/t", pdf_path]
        if printer:
            args.append(printer)
        commands.append(args)

    if sumatra:
        args = [sumatra, "-silent"]
        if printer:
            args.extend(["-print-to", printer, pdf_path])
        else:
            args.extend(["-print-to-default", pdf_path])
        commands.append(args)

    return commands


def _run_print_command(args: list[str]) -> None:
    subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def _shell_print_pdf(pdf_path: str, printer: str | None) -> None:
    import ctypes

    if printer:
        result = ctypes.windll.shell32.ShellExecuteW(
            None, "printto", pdf_path, f'"{printer}"', None, 0
        )
    else:
        os.startfile(pdf_path, "print")
        return

    if result <= 32:
        raise OSError(result, "ShellExecute failed", pdf_path)


def _windows_print_pdf(pdf_path: str, printer: str | None) -> None:
    errors: list[str] = []
    label_page, _ = _pdf_page_kind(pdf_path)

    try:
        _print_via_win32(pdf_path, printer, label_page)
        return
    except Exception as exc:
        errors.append(f"win32: {exc}")

    for args in _pdf_viewer_commands(pdf_path, printer):
        try:
            _run_print_command(args)
            return
        except OSError as exc:
            errors.append(f"{args[0]}: {exc}")

    try:
        _shell_print_pdf(pdf_path, printer)
        return
    except OSError as exc:
        errors.append(f"shell: {exc}")

    hint = (
        "Check that the selected printer is online and available."
    )
    detail = "; ".join(errors) if errors else "no PDF print handler available"
    raise PrintError(f"Could not print PDF ({detail}). {hint}")


def print_pdf(pdf_bytes: bytes, printer: str | None = None) -> str:
    job_id = str(uuid.uuid4())[:8]
    tmp_dir = tempfile.gettempdir()
    pdf_path = os.path.join(tmp_dir, f"wh_pallet_print_{job_id}.pdf")
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    if sys.platform == "win32":
        _windows_print_pdf(pdf_path, printer)
    else:
        # Dev fallback on macOS/Linux: open file instead of printing
        if sys.platform == "darwin":
            os.system(f'open "{pdf_path}"')
        else:
            os.system(f'xdg-open "{pdf_path}"')

    return pdf_path
