"""SQLAlchemy ORM — точное зеркало реальной схемы PostgreSQL (дамп 2025-05-25).

Схема использует VARCHAR + CHECK вместо PostgreSQL ENUM-типов.
Python-енумы здесь только для валидации на уровне приложения.
"""
import enum
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import (
    Boolean, CheckConstraint, Column, Date, DateTime,
    ForeignKey, Integer, Numeric, SmallInteger, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


# ── Python-перечисления (значения = реальные строки в БД) ─────────────────────

class CarStatus(str, enum.Enum):
    available      = "available"
    reserved       = "reserved"
    test_drive     = "test_drive"
    sold           = "sold"
    on_service     = "on_service"
    decommissioned = "decommissioned"

class CarType(str, enum.Enum):
    new  = "new"
    used = "used"

class BodyType(str, enum.Enum):
    sedan     = "sedan"
    hatchback = "hatchback"
    suv       = "suv"
    crossover = "crossover"
    minivan   = "minivan"
    pickup    = "pickup"
    coupe     = "coupe"
    universal = "universal"

class DealStatus(str, enum.Enum):
    draft     = "draft"
    signed    = "signed"
    paid      = "paid"
    delivered = "delivered"
    cancelled = "cancelled"

class PaymentType(str, enum.Enum):
    cash        = "cash"
    card        = "card"
    credit      = "credit"
    installment = "installment"

class PaymentMethod(str, enum.Enum):
    cash          = "cash"
    card          = "card"
    bank_transfer = "bank_transfer"
    credit        = "credit"

class TdResult(str, enum.Enum):
    interested     = "interested"
    not_interested = "not_interested"
    thinking       = "thinking"
    cancelled      = "cancelled"

class SoStatus(str, enum.Enum):
    open          = "open"
    in_progress   = "in_progress"
    waiting_parts = "waiting_parts"
    done          = "done"
    cancelled     = "cancelled"

class AuditAction(str, enum.Enum):
    login  = "login"
    logout = "logout"
    create = "create"
    update = "update"
    delete = "delete"

class AuditStatus(str, enum.Enum):
    success = "success"
    blocked = "blocked"
    error   = "error"


# ── СПРАВОЧНИКИ ───────────────────────────────────────────────────────────────

class Brand(Base):
    __tablename__ = "brand"
    id:      Mapped[int] = mapped_column(Integer, primary_key=True)
    name:    Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    models:  Mapped[list["Model"]] = relationship(back_populates="brand")


class Model(Base):
    __tablename__ = "model"
    id:        Mapped[int]      = mapped_column(Integer, primary_key=True)
    brand_id:  Mapped[int]      = mapped_column(ForeignKey("brand.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    name:      Mapped[str]      = mapped_column(String(100), nullable=False)
    body_type: Mapped[str]      = mapped_column(String(50), nullable=False)
    car_class: Mapped[str|None] = mapped_column(String(10))
    brand:     Mapped["Brand"]  = relationship(back_populates="models")
    cars:      Mapped[list["Car"]] = relationship(back_populates="model")

    __table_args__ = (UniqueConstraint("brand_id", "name"),)


class Department(Base):
    __tablename__ = "department"
    id:        Mapped[int] = mapped_column(Integer, primary_key=True)
    name:      Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    employees: Mapped[list["Employee"]] = relationship(back_populates="department")


# ── СУЩНОСТИ ──────────────────────────────────────────────────────────────────

class Car(Base):
    __tablename__ = "car"
    id:         Mapped[int]      = mapped_column(Integer, primary_key=True)
    model_id:   Mapped[int]      = mapped_column(ForeignKey("model.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    vin:        Mapped[str]      = mapped_column(String(17), nullable=False, unique=True)
    year:       Mapped[int]      = mapped_column(Integer, nullable=False)
    color:      Mapped[str]      = mapped_column(String(50), nullable=False)
    mileage:    Mapped[int]      = mapped_column(Integer, nullable=False, default=0)
    price:      Mapped[Decimal]  = mapped_column(Numeric(12, 2), nullable=False)
    status:     Mapped[str]      = mapped_column(String(30), nullable=False, default="available")
    type:       Mapped[str]      = mapped_column(String(10), nullable=False, default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    model:      Mapped["Model"]  = relationship(back_populates="cars")


class Employee(Base):
    __tablename__ = "employee"
    id:            Mapped[int]  = mapped_column(Integer, primary_key=True)
    department_id: Mapped[int]  = mapped_column(ForeignKey("department.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    full_name:     Mapped[str]  = mapped_column(String(200), nullable=False)
    position:      Mapped[str]  = mapped_column(String(100), nullable=False)
    phone:         Mapped[str]  = mapped_column(String(20), nullable=False, unique=True)  # NOT NULL в реальной схеме
    hire_date:     Mapped[date] = mapped_column(Date, nullable=False, server_default=func.current_date())
    is_active:     Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    department:    Mapped["Department"] = relationship(back_populates="employees")


class Client(Base):
    __tablename__ = "client"
    id:         Mapped[int]       = mapped_column(Integer, primary_key=True)
    full_name:  Mapped[str]       = mapped_column(String(200), nullable=False)
    phone:      Mapped[str]       = mapped_column(String(20), nullable=False, unique=True)
    email:      Mapped[str|None]  = mapped_column(String(150), unique=True)
    passport:   Mapped[str|None]  = mapped_column(String(20), unique=True)
    birth_date: Mapped[date|None] = mapped_column(Date)
    created_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── ТРАНЗАКЦИОННЫЕ ────────────────────────────────────────────────────────────

class TestDrive(Base):
    __tablename__ = "test_drive"
    id:           Mapped[int]      = mapped_column(Integer, primary_key=True)
    car_id:       Mapped[int]      = mapped_column(ForeignKey("car.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    client_id:    Mapped[int]      = mapped_column(ForeignKey("client.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    employee_id:  Mapped[int]      = mapped_column(ForeignKey("employee.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)  # без timezone
    duration_min: Mapped[int]      = mapped_column(Integer, nullable=False, default=30)
    result:       Mapped[str|None] = mapped_column(String(30))
    notes:        Mapped[str|None] = mapped_column(Text)


class Deal(Base):
    __tablename__ = "deal"
    id:           Mapped[int]     = mapped_column(Integer, primary_key=True)
    car_id:       Mapped[int]     = mapped_column(ForeignKey("car.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    client_id:    Mapped[int]     = mapped_column(ForeignKey("client.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    employee_id:  Mapped[int]     = mapped_column(ForeignKey("employee.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    deal_date:    Mapped[date]    = mapped_column(Date, nullable=False, server_default=func.current_date())
    amount:       Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payment_type: Mapped[str]     = mapped_column(String(30), nullable=False)
    status:       Mapped[str]     = mapped_column(String(30), nullable=False, default="draft")
    created_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    payments:     Mapped[list["Payment"]]     = relationship(back_populates="deal", cascade="all, delete-orphan")
    services:     Mapped[list["DealService"]] = relationship(back_populates="deal", cascade="all, delete-orphan")


class Payment(Base):
    __tablename__ = "payment"
    id:      Mapped[int]     = mapped_column(Integer, primary_key=True)
    deal_id: Mapped[int]     = mapped_column(ForeignKey("deal.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    amount:  Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    paid_at: Mapped[date]    = mapped_column(Date, nullable=False, server_default=func.current_date())  # DATE, не timestamp
    method:  Mapped[str]     = mapped_column(String(30), nullable=False)
    deal:    Mapped["Deal"]  = relationship(back_populates="payments")


class DealService(Base):
    __tablename__ = "deal_service"
    id:           Mapped[int]     = mapped_column(Integer, primary_key=True)
    deal_id:      Mapped[int]     = mapped_column(ForeignKey("deal.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    service_name: Mapped[str]     = mapped_column(String(200), nullable=False)
    price:        Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    deal:         Mapped["Deal"]  = relationship(back_populates="services")


class ServiceOrder(Base):
    __tablename__ = "service_order"
    id:          Mapped[int]       = mapped_column(Integer, primary_key=True)
    car_id:      Mapped[int]       = mapped_column(ForeignKey("car.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    client_id:   Mapped[int]       = mapped_column(ForeignKey("client.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    employee_id: Mapped[int]       = mapped_column(ForeignKey("employee.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    open_date:   Mapped[date]      = mapped_column(Date, nullable=False, server_default=func.current_date())
    close_date:  Mapped[date|None] = mapped_column(Date)
    status:      Mapped[str]       = mapped_column(String(30), nullable=False, default="open")  # 'open' не 'pending'
    total:       Mapped[Decimal]   = mapped_column(Numeric(12, 2), nullable=False, default=0)
    works:       Mapped[list["ServiceWork"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class ServiceWork(Base):
    __tablename__ = "service_work"
    id:               Mapped[int]     = mapped_column(Integer, primary_key=True)
    service_order_id: Mapped[int]     = mapped_column(ForeignKey("service_order.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    description:      Mapped[str]     = mapped_column(String(300), nullable=False)
    hours:            Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    unit_price:       Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    order:            Mapped["ServiceOrder"] = relationship(back_populates="works")


class AuditLog(Base):
    __tablename__ = "audit_log"
    id:        Mapped[int]      = mapped_column(Integer, primary_key=True)
    ts:        Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user_role: Mapped[str|None] = mapped_column(String(50))
    user_name: Mapped[str|None] = mapped_column(String(200))
    entity:    Mapped[str]      = mapped_column(String(50), nullable=False)
    action:    Mapped[str]      = mapped_column(String(20), nullable=False)
    record_id: Mapped[int|None] = mapped_column(Integer)
    status:    Mapped[str]      = mapped_column(String(20), nullable=False, default="success")
    details:   Mapped[str|None] = mapped_column(Text)
