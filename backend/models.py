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


class AppSetting(Base):
    __tablename__ = "app_setting"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False, default="")
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


SETTING_PRINTER = "printer_name"
SETTING_PRINT_FORMAT = "print_format"
SETTING_PRINT_ORIENTATION = "print_orientation"

PRINT_FORMAT_A4 = "a4"
PRINT_FORMAT_LABEL_10X15 = "label_10x15"
PRINT_ORIENTATION_PORTRAIT = "portrait"
PRINT_ORIENTATION_LANDSCAPE = "landscape"


def get_setting(db, key: str, default: str | None = None) -> str | None:
    row = db.get(AppSetting, key)
    return row.value if row else default


def set_setting(db, key: str, value: str) -> None:
    row = db.get(AppSetting, key)
    if row:
        row.value = value
    else:
        row = AppSetting(key=key, value=value)
        db.add(row)
    db.commit()
