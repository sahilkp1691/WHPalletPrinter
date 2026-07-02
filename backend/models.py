from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String

from .database import Base


def utcnow():
    return datetime.now(timezone.utc)


def normalize_art_num(art_num: str) -> str:
    return (art_num or "").strip().upper()


class ArticleQtyCarton(Base):
    __tablename__ = "article_qty_carton"

    art_num = Column(String, primary_key=True)
    qty_per_carton = Column(Integer, nullable=False)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)
