from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ArticleQtyCarton, normalize_art_num
from ..services.code128 import build_scan_payload, render_barcode_base64
from ..services.pdf_print import PrintRow, build_pdf, print_pdf

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

    pdf_bytes = build_pdf(print_rows)
    pdf_path = print_pdf(pdf_bytes)
    job_id = pdf_path.split("_")[-1].replace(".pdf", "")
    return PrintJobOut(job_id=job_id, row_count=len(print_rows), pdf_path=pdf_path)
