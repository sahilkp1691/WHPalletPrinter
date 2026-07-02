from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ArticleQtyCarton, normalize_art_num
from ..services.excel_io import create_template_xlsx, export_articles_xlsx, import_articles_xlsx

router = APIRouter(prefix="/api/articles", tags=["articles"])


class ArticleOut(BaseModel):
    art_num: str
    qty_per_carton: int
    updated_at: datetime


class ArticleUpsert(BaseModel):
    qty_per_carton: int = Field(gt=0)


class ArticleListOut(BaseModel):
    items: list[ArticleOut]
    total: int


@router.get("", response_model=ArticleListOut)
def list_articles(
    q: str = "",
    limit: int = Query(200, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(ArticleQtyCarton)
    if q.strip():
        needle = f"%{normalize_art_num(q)}%"
        query = query.filter(ArticleQtyCarton.art_num.like(needle))
    total = query.count()
    rows = (
        query.order_by(ArticleQtyCarton.art_num)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "items": [
            ArticleOut(
                art_num=r.art_num,
                qty_per_carton=r.qty_per_carton,
                updated_at=r.updated_at,
            )
            for r in rows
        ],
        "total": total,
    }


@router.get("/export")
def export_articles(db: Session = Depends(get_db)):
    data = export_articles_xlsx(db)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="article_qty_carton.xlsx"'},
    )


@router.get("/template")
def download_template():
    data = create_template_xlsx()
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="article_template.xlsx"'},
    )


@router.post("/import")
async def import_articles(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(400, "Upload an .xlsx file")
    data = await file.read()
    return import_articles_xlsx(db, data)


@router.get("/{art_num}", response_model=ArticleOut)
def get_article(art_num: str, db: Session = Depends(get_db)):
    key = normalize_art_num(art_num)
    row = db.get(ArticleQtyCarton, key)
    if not row:
        raise HTTPException(404, f"Art Num not found: {key}")
    return ArticleOut(
        art_num=row.art_num,
        qty_per_carton=row.qty_per_carton,
        updated_at=row.updated_at,
    )


@router.put("/{art_num}", response_model=ArticleOut)
def upsert_article(art_num: str, body: ArticleUpsert, db: Session = Depends(get_db)):
    key = normalize_art_num(art_num)
    if not key:
        raise HTTPException(400, "Art Num is required")
    row = db.get(ArticleQtyCarton, key)
    now = datetime.now(timezone.utc)
    if row:
        row.qty_per_carton = body.qty_per_carton
        row.updated_at = now
    else:
        row = ArticleQtyCarton(
            art_num=key,
            qty_per_carton=body.qty_per_carton,
            updated_at=now,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return ArticleOut(
        art_num=row.art_num,
        qty_per_carton=row.qty_per_carton,
        updated_at=row.updated_at,
    )


@router.delete("/{art_num}")
def delete_article(art_num: str, db: Session = Depends(get_db)):
    key = normalize_art_num(art_num)
    row = db.get(ArticleQtyCarton, key)
    if not row:
        raise HTTPException(404, f"Art Num not found: {key}")
    db.delete(row)
    db.commit()
    return {"deleted": key}
