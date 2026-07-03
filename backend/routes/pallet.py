from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.code128 import build_scan_payload, render_barcode_base64
from ..services.session_service import (
    CartonValidationError,
    add_carton_to_pallet,
    build_resolved_products,
    clear_pallet,
    get_pallet_assignments,
    lookup_carton_lines,
    remove_carton_from_pallet,
    require_active_session,
)

router = APIRouter(prefix="/api/pallet", tags=["pallet"])


class PalletCartonIn(BaseModel):
    pallet_num: str
    carton_scan: str


class CartonProductOut(BaseModel):
    stock_code: str
    qty_per_carton: int


class CartonScanOut(BaseModel):
    scan: str
    carton_id: int | None = None
    stock_code: str | None = None
    qty_per_carton: int | None = None
    products: list[CartonProductOut] = Field(default_factory=list)
    error: str | None = None


class PrintLineOut(BaseModel):
    art_num: str
    cartons: int
    qty_per_carton: int | None = None
    qty: int | None = None
    barcode_payload: str | None = None
    barcode_png_base64: str | None = None


class PalletStateOut(BaseModel):
    pallet_num: str
    carton_scans: list[CartonScanOut]
    rows: list[PrintLineOut]
    can_print: bool


def _build_pallet_state(db: Session, pallet_num: str) -> PalletStateOut:
    session = require_active_session(db)
    pallet_num = pallet_num.strip()
    assignments = get_pallet_assignments(db, session.id, pallet_num)

    scan_out: list[CartonScanOut] = []
    resolved = build_resolved_products(db, session.id, assignments)

    for assignment in assignments:
        try:
            carton_id, lines = lookup_carton_lines(db, session.id, assignment.scan_text)
        except CartonValidationError:
            carton_id = assignment.carton_id
            lines = []

        products = [
            CartonProductOut(stock_code=line.stock_code, qty_per_carton=line.qty_per_carton)
            for line in lines
        ]
        primary = lines[0] if lines else None
        scan_out.append(
            CartonScanOut(
                scan=assignment.scan_text,
                carton_id=carton_id,
                stock_code=primary.stock_code if primary and len(products) == 1 else None,
                qty_per_carton=primary.qty_per_carton if primary and len(products) == 1 else None,
                products=products,
            )
        )

    from collections import defaultdict

    agg_cartons: dict[str, int] = defaultdict(int)
    agg_qty: dict[str, int] = defaultdict(int)
    agg_qpc: dict[str, int] = {}
    for _cid, stock_code, qty_per_carton, _scan in resolved:
        agg_cartons[stock_code] += 1
        agg_qty[stock_code] += qty_per_carton
        agg_qpc[stock_code] = qty_per_carton

    preview_rows: list[PrintLineOut] = []
    for stock_code in sorted(agg_cartons.keys()):
        qty = agg_qty[stock_code]
        payload = build_scan_payload(stock_code, qty)
        preview_rows.append(
            PrintLineOut(
                art_num=stock_code,
                cartons=agg_cartons[stock_code],
                qty_per_carton=agg_qpc[stock_code],
                qty=qty,
                barcode_payload=payload,
                barcode_png_base64=render_barcode_base64(payload),
            )
        )

    return PalletStateOut(
        pallet_num=pallet_num,
        carton_scans=scan_out,
        rows=preview_rows,
        can_print=len(assignments) > 0 and len(preview_rows) > 0,
    )


@router.get("", response_model=PalletStateOut)
def get_pallet(pallet_num: str, db: Session = Depends(get_db)):
    if not pallet_num.strip():
        raise HTTPException(400, "pallet_num is required")
    return _build_pallet_state(db, pallet_num)


@router.post("/carton", response_model=PalletStateOut)
def add_carton(body: PalletCartonIn, db: Session = Depends(get_db)):
    try:
        add_carton_to_pallet(db, body.pallet_num, body.carton_scan)
    except CartonValidationError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _build_pallet_state(db, body.pallet_num)


@router.delete("/carton", response_model=PalletStateOut)
def delete_carton(body: PalletCartonIn, db: Session = Depends(get_db)):
    remove_carton_from_pallet(db, body.pallet_num, body.carton_scan)
    return _build_pallet_state(db, body.pallet_num)


@router.delete("", response_model=dict)
def delete_pallet(pallet_num: str, db: Session = Depends(get_db)):
    if not pallet_num.strip():
        raise HTTPException(400, "pallet_num is required")
    clear_pallet(db, pallet_num)
    return {"cleared": True}
