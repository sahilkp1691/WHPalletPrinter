from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.packlist_io import create_packlist_template_xlsx, parse_packlist_xlsx
from ..services.session_service import (
    build_dashboard,
    get_active_session,
    import_packlist_session,
    session_status,
)
from ..models import SESSION_ARCHIVED, utcnow

router = APIRouter(prefix="/api/packlist", tags=["packlist"])


class PacklistStatusOut(BaseModel):
    loaded: bool
    session_id: int | None = None
    filename: str | None = None
    imported_at: str | None = None
    line_count: int = 0
    carton_count: int = 0
    assigned_cartons: int = 0
    remaining_cartons: int = 0
    pallet_count: int = 0
    printed_pallet_count: int = 0
    warnings: list[str] = []


class PacklistImportOut(BaseModel):
    loaded: bool
    session_id: int | None = None
    filename: str
    line_count: int
    carton_count: int
    errors: list[str]
    warnings: list[str]


@router.get("", response_model=PacklistStatusOut)
def packlist_status(db: Session = Depends(get_db)):
    session = get_active_session(db)
    data = session_status(db, session)
    return PacklistStatusOut(**data)


@router.get("/dashboard")
def packlist_dashboard(db: Session = Depends(get_db)):
    return build_dashboard(db)


@router.get("/template")
def download_template():
    data = create_packlist_template_xlsx()
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="packlist_template.xlsx"'},
    )


@router.post("/import", response_model=PacklistImportOut)
async def import_packlist(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(400, "Upload an .xlsx file")

    data = await file.read()
    result = parse_packlist_xlsx(data)

    if result.errors or not result.lines:
        return PacklistImportOut(
            loaded=False,
            filename=file.filename,
            line_count=0,
            carton_count=0,
            errors=result.errors or ["No valid packlist rows found"],
            warnings=result.warnings,
        )

    session = import_packlist_session(db, result, filename=file.filename)
    status = session_status(db, session)
    return PacklistImportOut(
        loaded=True,
        session_id=session.id,
        filename=file.filename,
        line_count=status["line_count"],
        carton_count=status["carton_count"],
        errors=[],
        warnings=result.warnings,
    )


@router.delete("")
def delete_packlist(db: Session = Depends(get_db)):
    session = get_active_session(db)
    if session:
        session.status = SESSION_ARCHIVED
        session.imported_at = session.imported_at or utcnow()
        db.commit()
    return {"cleared": True}
