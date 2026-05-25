"""Сделки — главная бизнес-сущность. Триггеры PostgreSQL делают всю работу."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import DBAPIError

from auth import TokenData, get_current_user, require_roles
from database import get_db
from models import (
    AuditLog, AuditAction, AuditStatus,
    Car, Client, Deal, DealService, DealStatus, Employee,
    Model, Brand, Payment, PaymentMethod, PaymentType,
)

router = APIRouter(prefix="/deals", tags=["deals"])


class DealCreate(BaseModel):
    car_id: int; client_id: int; employee_id: int
    amount: float; payment_type: PaymentType
    status: DealStatus = DealStatus.draft


class DealUpdate(BaseModel):
    status: DealStatus | None = None
    amount: float | None = None
    payment_type: PaymentType | None = None


class PaymentCreate(BaseModel):
    amount: float; method: PaymentMethod


class ServiceCreate(BaseModel):
    service_name: str; price: float


async def _enrich_deal(deal: Deal, db: AsyncSession) -> dict:
    car = await db.get(Car, deal.car_id)
    model = await db.get(Model, car.model_id) if car else None
    brand = await db.get(Brand, model.brand_id) if model else None
    client = await db.get(Client, deal.client_id)
    emp = await db.get(Employee, deal.employee_id)

    paid_res = await db.execute(
        text("SELECT fn_deal_paid_amount(:did)"), {"did": deal.id}
    )
    paid = paid_res.scalar() or 0

    svcs_res = (await db.execute(
        select(DealService).where(DealService.deal_id == deal.id)
    )).scalars().all()
    services_total = sum(float(s.price) for s in svcs_res)

    pmts_res = (await db.execute(
        select(Payment).where(Payment.deal_id == deal.id)
    )).scalars().all()

    d = {c.name: getattr(deal, c.name) for c in Deal.__table__.columns}
    d["car"]        = f"{brand.name} {model.name}" if brand and model else None
    d["vin"]        = car.vin if car else None
    d["client"]     = client.full_name if client else None
    d["employee"]   = emp.full_name if emp else None
    d["paid"]       = float(paid)
    d["remaining"]  = float(deal.amount) + services_total - float(paid)
    d["services"]   = [{"id": s.id, "service_name": s.service_name, "price": float(s.price)} for s in svcs_res]
    d["payments"]   = [{"id": p.id, "amount": float(p.amount), "paid_at": p.paid_at, "method": p.method} for p in pmts_res]
    return d


@router.get("/")
async def list_deals(db: AsyncSession = Depends(get_db), _: TokenData = Depends(get_current_user)):
    deals = (await db.execute(select(Deal).order_by(Deal.deal_date.desc()))).scalars().all()
    return [await _enrich_deal(d, db) for d in deals]


@router.get("/{deal_id}")
async def get_deal(deal_id: int, db: AsyncSession = Depends(get_db), _: TokenData = Depends(get_current_user)):
    deal = await db.get(Deal, deal_id)
    if not deal:
        raise HTTPException(404, "Сделка не найдена")
    return await _enrich_deal(deal, db)


@router.post("/", status_code=201)
async def create_deal(
    body: DealCreate,
    db: AsyncSession = Depends(get_db),
    user: TokenData = Depends(require_roles("manager", "admin")),
):
    deal = Deal(**body.model_dump())
    db.add(deal)
    try:
        await db.commit()
    except DBAPIError as e:
        await db.rollback()
        # Триггер PostgreSQL бросает RAISE EXCEPTION — прокидываем его клиенту
        raise HTTPException(400, str(e.orig).split("\n")[0])
    await db.refresh(deal)

    db.add(AuditLog(user_role=user.role, user_name=user.name, entity="deal",
                    action=AuditAction.create, record_id=deal.id, status=AuditStatus.success,
                    details=f"Создана сделка №{deal.id}, сумма {deal.amount}"))
    await db.commit()
    return await _enrich_deal(deal, db)


@router.patch("/{deal_id}")
async def update_deal(
    deal_id: int, body: DealUpdate,
    db: AsyncSession = Depends(get_db),
    user: TokenData = Depends(require_roles("manager", "admin")),
):
    deal = await db.get(Deal, deal_id)
    if not deal:
        raise HTTPException(404)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(deal, k, v)
    try:
        await db.commit()
    except DBAPIError as e:
        await db.rollback()
        raise HTTPException(400, str(e.orig).split("\n")[0])
    await db.refresh(deal)

    db.add(AuditLog(user_role=user.role, user_name=user.name, entity="deal",
                    action=AuditAction.update, record_id=deal.id, status=AuditStatus.success,
                    details=f"Обновлена сделка №{deal.id} → статус {deal.status}"))
    await db.commit()
    return await _enrich_deal(deal, db)


@router.delete("/{deal_id}", status_code=204)
async def delete_deal(
    deal_id: int,
    db: AsyncSession = Depends(get_db),
    _: TokenData = Depends(require_roles("manager", "admin")),
):
    deal = await db.get(Deal, deal_id)
    if not deal:
        raise HTTPException(404)
    await db.delete(deal)
    await db.commit()


# ── Платежи по сделке ──────────────────────────────────────────────────────

@router.post("/{deal_id}/payments", status_code=201)
async def add_payment(
    deal_id: int, body: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    user: TokenData = Depends(require_roles("manager", "admin")),
):
    deal = await db.get(Deal, deal_id)
    if not deal:
        raise HTTPException(404)
    pmt = Payment(deal_id=deal_id, amount=body.amount, method=body.method)
    db.add(pmt)
    try:
        await db.commit()
    except DBAPIError as e:
        await db.rollback()
        raise HTTPException(400, str(e.orig).split("\n")[0])
    await db.refresh(pmt)

    db.add(AuditLog(user_role=user.role, user_name=user.name, entity="payment",
                    action=AuditAction.create, record_id=pmt.id, status=AuditStatus.success,
                    details=f"Платёж {pmt.amount} по сделке №{deal_id} ({pmt.method})"))
    await db.commit()
    return pmt


@router.delete("/{deal_id}/payments/{payment_id}", status_code=204)
async def delete_payment(
    deal_id: int, payment_id: int,
    db: AsyncSession = Depends(get_db),
    _: TokenData = Depends(require_roles("manager", "admin")),
):
    pmt = await db.get(Payment, payment_id)
    if not pmt or pmt.deal_id != deal_id:
        raise HTTPException(404)
    await db.delete(pmt)
    await db.commit()


# ── Доп. услуги по сделке ─────────────────────────────────────────────────

@router.post("/{deal_id}/services", status_code=201)
async def add_service(
    deal_id: int, body: ServiceCreate,
    db: AsyncSession = Depends(get_db),
    user: TokenData = Depends(require_roles("manager", "admin")),
):
    svc = DealService(deal_id=deal_id, **body.model_dump())
    db.add(svc)
    await db.commit()
    await db.refresh(svc)
    return svc


@router.delete("/{deal_id}/services/{svc_id}", status_code=204)
async def delete_service(
    deal_id: int, svc_id: int,
    db: AsyncSession = Depends(get_db),
    _: TokenData = Depends(require_roles("manager", "admin")),
):
    svc = await db.get(DealService, svc_id)
    if not svc or svc.deal_id != deal_id:
        raise HTTPException(404)
    await db.delete(svc)
    await db.commit()
