from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    ArticleQtyCarton,
    PRINT_FORMAT_A4,
    PRINT_FORMAT_LABEL_10X15,
    PRINT_ORIENTATION_LANDSCAPE,
    PRINT_ORIENTATION_PORTRAIT,
    SETTING_PRINT_FORMAT,
    SETTING_PRINT_ORIENTATION,
    SETTING_PRINTER,
    get_setting,
    normalize_art_num,
    set_setting,
)
from ..services.code128 import build_scan_payload, render_barcode_base64
from ..services.pdf_print import PrintError, PrintRow, build_pdf, print_pdf
from ..services.printers import get_default_printer, list_printers

router = APIRouter(prefix="/api/print", tags=["print"])


class PrintLineIn(BaseModel):
    art_num: str
    cartons: int = Field(gt=0)


class PrintLineOut(BaseModel):
    art_num: str
    cartons: int
    qty_per_carton: int | None = None
    qty: int | None = None
    barcode_payload: str | None = None
    barcode_png_base64: str | None = None
    error: str | None = None


class PrintPreviewOut(BaseModel):
    rows: list[PrintLineOut]
    can_print: bool


class PrintJobOut(BaseModel):
    job_id: str
    row_count: int
    pdf_path: str
    printer: str | None = None


class PrintersOut(BaseModel):
    printers: list[str]
    default: str | None = None
    selected: str | None = None
    format: str = PRINT_FORMAT_A4
    orientation: str = PRINT_ORIENTATION_PORTRAIT


class PrinterIn(BaseModel):
    printer: str | None = None
    format: str | None = None
    orientation: str | None = None


def _normalize_format(value: str | None) -> str:
    if value == PRINT_FORMAT_LABEL_10X15:
        return PRINT_FORMAT_LABEL_10X15
    return PRINT_FORMAT_A4


def _normalize_orientation(value: str | None) -> str:
    if value == PRINT_ORIENTATION_LANDSCAPE:
        return PRINT_ORIENTATION_LANDSCAPE
    return PRINT_ORIENTATION_PORTRAIT


def _read_print_settings(db: Session) -> tuple[str | None, str, str]:
    printers = list_printers()
    selected = get_setting(db, SETTING_PRINTER) or None
    if selected and selected not in printers:
        selected = None
    fmt = _normalize_format(get_setting(db, SETTING_PRINT_FORMAT))
    orientation = _normalize_orientation(get_setting(db, SETTING_PRINT_ORIENTATION))
    return selected, fmt, orientation


def _resolve_rows(lines: list[PrintLineIn], db: Session) -> tuple[list[PrintLineOut], list[PrintRow]]:
    out: list[PrintLineOut] = []
    resolved: list[PrintRow] = []

    for line in lines:
        key = normalize_art_num(line.art_num)
        if not key:
            out.append(
                PrintLineOut(
                    art_num=line.art_num,
                    cartons=line.cartons,
                    error="Art Num is required",
                )
            )
            continue

        article = db.get(ArticleQtyCarton, key)
        if not article:
            out.append(
                PrintLineOut(
                    art_num=key,
                    cartons=line.cartons,
                    error=f"Art Num not found: {key}",
                )
            )
            continue

        qty = line.cartons * article.qty_per_carton
        payload = build_scan_payload(key, qty)
        out.append(
            PrintLineOut(
                art_num=key,
                cartons=line.cartons,
                qty_per_carton=article.qty_per_carton,
                qty=qty,
                barcode_payload=payload,
                barcode_png_base64=render_barcode_base64(payload),
            )
        )
        resolved.append(
            PrintRow(
                art_num=key,
                cartons=line.cartons,
                qty_per_carton=article.qty_per_carton,
                qty=qty,
            )
        )

    return out, resolved


@router.get("/printers", response_model=PrintersOut)
def get_printers(db: Session = Depends(get_db)):
    selected, fmt, orientation = _read_print_settings(db)
    return PrintersOut(
        printers=list_printers(),
        default=get_default_printer(),
        selected=selected,
        format=fmt,
        orientation=orientation,
    )


@router.put("/printers", response_model=PrintersOut)
def set_printer(body: PrinterIn, db: Session = Depends(get_db)):
    if body.printer is not None:
        set_setting(db, SETTING_PRINTER, body.printer or "")
    if body.format is not None:
        set_setting(db, SETTING_PRINT_FORMAT, _normalize_format(body.format))
    if body.orientation is not None:
        set_setting(db, SETTING_PRINT_ORIENTATION, _normalize_orientation(body.orientation))
    return get_printers(db)


@router.post("/preview", response_model=PrintPreviewOut)
def preview_print(lines: list[PrintLineIn], db: Session = Depends(get_db)):
    if not lines:
        raise HTTPException(400, "At least one row is required")
    rows, _ = _resolve_rows(lines, db)
    can_print = all(r.error is None for r in rows)
    return PrintPreviewOut(rows=rows, can_print=can_print)


@router.post("", response_model=PrintJobOut)
def print_labels(lines: list[PrintLineIn], db: Session = Depends(get_db)):
    if not lines:
        raise HTTPException(400, "At least one row is required")

    preview_rows, print_rows = _resolve_rows(lines, db)
    if not all(r.error is None for r in preview_rows):
        errors = [r.error for r in preview_rows if r.error]
        raise HTTPException(400, {"message": "Cannot print with errors", "errors": errors})

    selected, fmt, orientation = _read_print_settings(db)

    pdf_bytes = build_pdf(print_rows, print_format=fmt, orientation=orientation)
    try:
        pdf_path = print_pdf(pdf_bytes, printer=selected)
    except PrintError as exc:
        raise HTTPException(500, str(exc)) from exc
    job_id = pdf_path.split("_")[-1].replace(".pdf", "")
    return PrintJobOut(
        job_id=job_id,
        row_count=len(print_rows),
        pdf_path=pdf_path,
        printer=selected,
    )
