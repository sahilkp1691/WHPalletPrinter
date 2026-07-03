from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    PRINT_FORMAT_A4,
    PRINT_FORMAT_LABEL_10X15,
    PRINT_ORIENTATION_LANDSCAPE,
    PRINT_ORIENTATION_PORTRAIT,
    SETTING_PRINT_FORMAT,
    SETTING_PRINT_ORIENTATION,
    SETTING_PRINTER,
    get_setting,
    set_setting,
)
from ..services.pdf_print import PrintError, PrintRow, build_pdf, print_pdf
from ..services.printers import get_default_printer, list_printers
from ..services.session_service import mark_pallet_printed, require_active_session
from .pallet import PrintLineOut, PalletStateOut, _build_pallet_state

router = APIRouter(prefix="/api/print", tags=["print"])


class PalletPrintIn(BaseModel):
    pallet_num: str


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


@router.post("/preview", response_model=PalletStateOut)
def preview_print(body: PalletPrintIn, db: Session = Depends(get_db)):
    if not body.pallet_num.strip():
        raise HTTPException(400, "Pallet number is required")
    return _build_pallet_state(db, body.pallet_num)


@router.post("", response_model=PrintJobOut)
def print_labels(body: PalletPrintIn, db: Session = Depends(get_db)):
    pallet_num = body.pallet_num.strip()
    if not pallet_num:
        raise HTTPException(400, "Pallet number is required")

    session = require_active_session(db)
    state = _build_pallet_state(db, pallet_num)
    if not state.can_print:
        raise HTTPException(400, "No cartons on this pallet to print")

    print_rows = [
        PrintRow(
            art_num=row.art_num,
            cartons=row.cartons,
            qty_per_carton=row.qty_per_carton or 0,
            qty=row.qty or 0,
            pallet_num=pallet_num,
        )
        for row in state.rows
    ]

    selected, fmt, orientation = _read_print_settings(db)

    pdf_bytes = build_pdf(print_rows, print_format=fmt, orientation=orientation)
    try:
        pdf_path = print_pdf(pdf_bytes, printer=selected)
    except PrintError as exc:
        raise HTTPException(500, str(exc)) from exc

    mark_pallet_printed(db, session.id, pallet_num)

    job_id = pdf_path.split("_")[-1].replace(".pdf", "")
    return PrintJobOut(
        job_id=job_id,
        row_count=len(print_rows),
        pdf_path=pdf_path,
        printer=selected,
    )
