from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from .database import Base


def utcnow():
    return datetime.now(timezone.utc)


def normalize_art_num(art_num: str) -> str:
    return (art_num or "").strip().upper()


SESSION_ACTIVE = "active"
SESSION_ARCHIVED = "archived"


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


class PacklistSession(Base):
    __tablename__ = "packlist_session"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String, nullable=False, default="")
    imported_at = Column(DateTime, nullable=False, default=utcnow)
    status = Column(String, nullable=False, default=SESSION_ACTIVE)
    warnings_json = Column(Text, nullable=False, default="[]")

    lines = relationship("PacklistLineRow", back_populates="session", cascade="all, delete-orphan")
    pallets = relationship("Pallet", back_populates="session", cascade="all, delete-orphan")
    carton_entries = relationship(
        "PacklistCartonEntry", back_populates="session", cascade="all, delete-orphan"
    )


class PacklistLineRow(Base):
    __tablename__ = "packlist_line"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("packlist_session.id"), nullable=False)
    row_num = Column(Integer, nullable=False)
    carton_spec = Column(String, nullable=False)
    stock_code = Column(String, nullable=False)
    total_qty = Column(Integer, nullable=False)
    qty_per_carton = Column(Integer, nullable=False)
    num_cartons = Column(Integer, nullable=False)

    session = relationship("PacklistSession", back_populates="lines")
    carton_entries = relationship("PacklistCartonEntry", back_populates="line", cascade="all, delete-orphan")


class PacklistCartonEntry(Base):
    __tablename__ = "packlist_carton_entry"
    __table_args__ = (UniqueConstraint("session_id", "carton_id", "line_id", name="uq_session_carton_line"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("packlist_session.id"), nullable=False)
    carton_id = Column(Integer, nullable=False)
    line_id = Column(Integer, ForeignKey("packlist_line.id"), nullable=False)

    session = relationship("PacklistSession", back_populates="carton_entries")
    line = relationship("PacklistLineRow", back_populates="carton_entries")


class Pallet(Base):
    __tablename__ = "pallet"
    __table_args__ = (UniqueConstraint("session_id", "pallet_num", name="uq_session_pallet_num"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("packlist_session.id"), nullable=False)
    pallet_num = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    printed_at = Column(DateTime, nullable=True)

    session = relationship("PacklistSession", back_populates="pallets")
    assignments = relationship("CartonAssignment", back_populates="pallet", cascade="all, delete-orphan")


class CartonAssignment(Base):
    __tablename__ = "carton_assignment"
    __table_args__ = (UniqueConstraint("session_id", "carton_id", name="uq_session_carton_assignment"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("packlist_session.id"), nullable=False)
    carton_id = Column(Integer, nullable=False)
    pallet_id = Column(Integer, ForeignKey("pallet.id"), nullable=False)
    scan_text = Column(String, nullable=False, default="")
    assigned_at = Column(DateTime, nullable=False, default=utcnow)

    pallet = relationship("Pallet", back_populates="assignments")


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
