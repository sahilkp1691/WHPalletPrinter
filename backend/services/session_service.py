import json
from collections import defaultdict
from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from ..models import (
    SESSION_ACTIVE,
    SESSION_ARCHIVED,
    CartonAssignment,
    PacklistCartonEntry,
    PacklistLineRow,
    PacklistSession,
    Pallet,
    utcnow,
)
from .packlist_io import PacklistParseResult, parse_carton_scan


class CartonValidationError(Exception):
    def __init__(self, message: str, code: str = "invalid"):
        super().__init__(message)
        self.code = code


@dataclass
class ResolvedCartonLine:
    stock_code: str
    qty_per_carton: int


def get_active_session(db: Session) -> PacklistSession | None:
    return (
        db.query(PacklistSession)
        .filter(PacklistSession.status == SESSION_ACTIVE)
        .order_by(PacklistSession.imported_at.desc())
        .first()
    )


def require_active_session(db: Session) -> PacklistSession:
    session = get_active_session(db)
    if not session:
        raise HTTPException(400, "Import a packlist first")
    return session


def import_packlist_session(
    db: Session, result: PacklistParseResult, filename: str
) -> PacklistSession:
    for existing in db.query(PacklistSession).filter(PacklistSession.status == SESSION_ACTIVE).all():
        existing.status = SESSION_ARCHIVED

    session = PacklistSession(
        filename=filename,
        imported_at=utcnow(),
        status=SESSION_ACTIVE,
        warnings_json=json.dumps(result.warnings),
    )
    db.add(session)
    db.flush()

    for parsed in result.lines:
        row = PacklistLineRow(
            session_id=session.id,
            row_num=parsed.row_num,
            carton_spec=parsed.carton_spec,
            stock_code=parsed.stock_code,
            total_qty=parsed.total_qty,
            qty_per_carton=parsed.qty_per_carton,
            num_cartons=parsed.num_cartons,
        )
        db.add(row)
        db.flush()

        for carton_id in parsed.carton_ids:
            db.add(
                PacklistCartonEntry(
                    session_id=session.id,
                    carton_id=carton_id,
                    line_id=row.id,
                )
            )

    db.commit()
    db.refresh(session)
    return session


def lookup_carton_lines(db: Session, session_id: int, raw_scan: str) -> tuple[int, list[ResolvedCartonLine]]:
    carton_id = parse_carton_scan(raw_scan)
    if carton_id is None:
        raise CartonValidationError(f"Invalid carton number: {raw_scan!r}", "invalid")

    entries = (
        db.query(PacklistCartonEntry)
        .options(joinedload(PacklistCartonEntry.line))
        .filter(
            PacklistCartonEntry.session_id == session_id,
            PacklistCartonEntry.carton_id == carton_id,
        )
        .all()
    )
    if not entries:
        raise CartonValidationError(f"Carton not in packlist: {carton_id}", "not_found")

    lines = [
        ResolvedCartonLine(stock_code=e.line.stock_code, qty_per_carton=e.line.qty_per_carton)
        for e in entries
    ]
    return carton_id, lines


def get_or_create_pallet(db: Session, session_id: int, pallet_num: str) -> Pallet:
    pallet = (
        db.query(Pallet)
        .filter(Pallet.session_id == session_id, Pallet.pallet_num == pallet_num)
        .first()
    )
    if pallet:
        return pallet
    pallet = Pallet(session_id=session_id, pallet_num=pallet_num, created_at=utcnow())
    db.add(pallet)
    db.flush()
    return pallet


def get_carton_assignment(db: Session, session_id: int, carton_id: int) -> CartonAssignment | None:
    return (
        db.query(CartonAssignment)
        .options(joinedload(CartonAssignment.pallet))
        .filter(
            CartonAssignment.session_id == session_id,
            CartonAssignment.carton_id == carton_id,
        )
        .first()
    )


def validate_carton_for_pallet(
    db: Session,
    session_id: int,
    pallet_id: int,
    carton_id: int,
) -> None:
    existing = get_carton_assignment(db, session_id, carton_id)
    if not existing:
        return
    if existing.pallet_id == pallet_id:
        raise CartonValidationError(
            f"Carton {carton_id} is already on this pallet",
            "duplicate_pallet",
        )
    raise CartonValidationError(
        f"Carton {carton_id} is already on pallet {existing.pallet.pallet_num}",
        "other_pallet",
    )


def add_carton_to_pallet(
    db: Session, pallet_num: str, carton_scan: str
) -> tuple[Pallet, int, list[ResolvedCartonLine]]:
    session = require_active_session(db)
    pallet_num = pallet_num.strip()
    if not pallet_num:
        raise HTTPException(400, "Pallet number is required")

    scan_text = carton_scan.strip()
    if not scan_text:
        raise HTTPException(400, "Carton scan is required")

    carton_id, lines = lookup_carton_lines(db, session.id, scan_text)
    pallet = get_or_create_pallet(db, session.id, pallet_num)
    if pallet.printed_at is not None:
        raise HTTPException(400, f"Pallet {pallet_num} has already been printed")

    validate_carton_for_pallet(db, session.id, pallet.id, carton_id)

    db.add(
        CartonAssignment(
            session_id=session.id,
            carton_id=carton_id,
            pallet_id=pallet.id,
            scan_text=scan_text,
            assigned_at=utcnow(),
        )
    )
    db.commit()
    db.refresh(pallet)
    return pallet, carton_id, lines


def remove_carton_from_pallet(db: Session, pallet_num: str, carton_scan: str) -> None:
    session = require_active_session(db)
    pallet_num = pallet_num.strip()
    scan_text = carton_scan.strip()

    pallet = (
        db.query(Pallet)
        .filter(Pallet.session_id == session.id, Pallet.pallet_num == pallet_num)
        .first()
    )
    if not pallet:
        return
    if pallet.printed_at is not None:
        raise HTTPException(400, f"Pallet {pallet_num} has already been printed")

    carton_id = parse_carton_scan(scan_text)
    if carton_id is None:
        raise HTTPException(400, f"Invalid carton number: {scan_text!r}")

    assignment = (
        db.query(CartonAssignment)
        .filter(
            CartonAssignment.pallet_id == pallet.id,
            CartonAssignment.carton_id == carton_id,
        )
        .first()
    )
    if assignment:
        db.delete(assignment)
        db.commit()


def clear_pallet(db: Session, pallet_num: str) -> None:
    session = require_active_session(db)
    pallet_num = pallet_num.strip()
    pallet = (
        db.query(Pallet)
        .filter(Pallet.session_id == session.id, Pallet.pallet_num == pallet_num)
        .first()
    )
    if not pallet:
        return
    if pallet.printed_at is not None:
        raise HTTPException(400, f"Pallet {pallet_num} has already been printed")

    db.query(CartonAssignment).filter(CartonAssignment.pallet_id == pallet.id).delete()
    db.delete(pallet)
    db.commit()


def get_pallet_assignments(db: Session, session_id: int, pallet_num: str) -> list[CartonAssignment]:
    pallet = (
        db.query(Pallet)
        .filter(Pallet.session_id == session_id, Pallet.pallet_num == pallet_num.strip())
        .first()
    )
    if not pallet:
        return []
    return (
        db.query(CartonAssignment)
        .filter(CartonAssignment.pallet_id == pallet.id)
        .order_by(CartonAssignment.assigned_at)
        .all()
    )


def build_resolved_products(
    db: Session, session_id: int, assignments: list[CartonAssignment]
) -> list[tuple[int, str, int, str]]:
    """Return (carton_id, stock_code, qty_per_carton, scan_text) per product line."""
    resolved: list[tuple[int, str, int, str]] = []
    for assignment in assignments:
        _cid, lines = lookup_carton_lines(db, session_id, str(assignment.carton_id))
        for line in lines:
            resolved.append((assignment.carton_id, line.stock_code, line.qty_per_carton, assignment.scan_text))
    return resolved


def aggregate_print_rows(
    pallet_num: str,
    resolved: list[tuple[int, str, int, str]],
) -> list[dict]:
    agg_cartons: dict[str, int] = defaultdict(int)
    agg_qty: dict[str, int] = defaultdict(int)
    agg_qpc: dict[str, int] = {}

    for _cid, stock_code, qty_per_carton, _scan in resolved:
        agg_cartons[stock_code] += 1
        agg_qty[stock_code] += qty_per_carton
        agg_qpc[stock_code] = qty_per_carton

    rows = []
    for stock_code in sorted(agg_cartons.keys()):
        rows.append(
            {
                "art_num": stock_code,
                "cartons": agg_cartons[stock_code],
                "qty_per_carton": agg_qpc[stock_code],
                "qty": agg_qty[stock_code],
                "pallet_num": pallet_num,
            }
        )
    return rows


def mark_pallet_printed(db: Session, session_id: int, pallet_num: str) -> Pallet:
    pallet = (
        db.query(Pallet)
        .filter(Pallet.session_id == session_id, Pallet.pallet_num == pallet_num.strip())
        .first()
    )
    if not pallet:
        raise HTTPException(400, "Pallet not found")
    if pallet.printed_at is None:
        pallet.printed_at = utcnow()
        db.commit()
        db.refresh(pallet)
    return pallet


def session_status(db: Session, session: PacklistSession | None) -> dict:
    if not session:
        return {"loaded": False}

    warnings = json.loads(session.warnings_json or "[]")
    line_count = db.query(PacklistLineRow).filter(PacklistLineRow.session_id == session.id).count()
    carton_count = (
        db.query(PacklistCartonEntry.carton_id)
        .filter(PacklistCartonEntry.session_id == session.id)
        .distinct()
        .count()
    )
    assigned_count = (
        db.query(CartonAssignment.carton_id)
        .filter(CartonAssignment.session_id == session.id)
        .distinct()
        .count()
    )
    pallet_count = db.query(Pallet).filter(Pallet.session_id == session.id).count()
    printed_count = (
        db.query(Pallet).filter(Pallet.session_id == session.id, Pallet.printed_at.isnot(None)).count()
    )

    return {
        "loaded": True,
        "session_id": session.id,
        "filename": session.filename,
        "imported_at": session.imported_at.isoformat(),
        "line_count": line_count,
        "carton_count": carton_count,
        "assigned_cartons": assigned_count,
        "remaining_cartons": max(0, carton_count - assigned_count),
        "pallet_count": pallet_count,
        "printed_pallet_count": printed_count,
        "warnings": warnings,
    }


def build_dashboard(db: Session) -> dict:
    session = get_active_session(db)
    if not session:
        return {"loaded": False}

    status = session_status(db, session)

    assignments = (
        db.query(CartonAssignment)
        .options(joinedload(CartonAssignment.pallet))
        .filter(CartonAssignment.session_id == session.id)
        .all()
    )
    assignment_by_carton = {a.carton_id: a for a in assignments}

    entries = (
        db.query(PacklistCartonEntry)
        .options(joinedload(PacklistCartonEntry.line))
        .filter(PacklistCartonEntry.session_id == session.id)
        .order_by(PacklistCartonEntry.carton_id)
        .all()
    )

    carton_map: dict[int, dict] = {}
    for entry in entries:
        item = carton_map.setdefault(
            entry.carton_id,
            {
                "carton_id": entry.carton_id,
                "carton_spec": entry.line.carton_spec,
                "products": [],
                "status": "remaining",
                "pallet_num": None,
                "printed": False,
            },
        )
        product = {"stock_code": entry.line.stock_code, "qty_per_carton": entry.line.qty_per_carton}
        if product not in item["products"]:
            item["products"].append(product)

    for carton_id, item in carton_map.items():
        assignment = assignment_by_carton.get(carton_id)
        if assignment:
            item["status"] = "assigned"
            item["pallet_num"] = assignment.pallet.pallet_num
            item["printed"] = assignment.pallet.printed_at is not None

    cartons = [carton_map[cid] for cid in sorted(carton_map.keys())]

    lines = (
        db.query(PacklistLineRow)
        .filter(PacklistLineRow.session_id == session.id)
        .order_by(PacklistLineRow.row_num)
        .all()
    )
    line_rows = [
        {
            "row_num": line.row_num,
            "carton_spec": line.carton_spec,
            "stock_code": line.stock_code,
            "total_qty": line.total_qty,
            "qty_per_carton": line.qty_per_carton,
            "num_cartons": line.num_cartons,
        }
        for line in lines
    ]

    pallets = (
        db.query(Pallet)
        .options(joinedload(Pallet.assignments))
        .filter(Pallet.session_id == session.id)
        .order_by(Pallet.created_at.desc())
        .all()
    )
    pallet_rows = [
        {
            "pallet_num": p.pallet_num,
            "carton_count": len(p.assignments),
            "printed": p.printed_at is not None,
            "created_at": p.created_at.isoformat(),
            "printed_at": p.printed_at.isoformat() if p.printed_at else None,
        }
        for p in pallets
    ]

    return {
        "loaded": True,
        "session": {
            "id": session.id,
            "filename": session.filename,
            "imported_at": session.imported_at.isoformat(),
        },
        "summary": {
            "total_cartons": status["carton_count"],
            "assigned_cartons": status["assigned_cartons"],
            "remaining_cartons": status["remaining_cartons"],
            "line_count": status["line_count"],
            "pallet_count": status["pallet_count"],
            "printed_pallet_count": status["printed_pallet_count"],
        },
        "cartons": cartons,
        "lines": line_rows,
        "pallets": pallet_rows,
    }
