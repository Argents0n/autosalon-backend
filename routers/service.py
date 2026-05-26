from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from auth import TokenData, get_current_user, require_roles
from database import get_db
from models import AuditLog, AuditAction, AuditStatus, ServiceOrder, ServiceWork, SoStatus
# Реальные статусы наряда: open, in_progress, waiting_parts, done, cancelled

router = APIRouter(prefix="/service-orders", tags=["service"])


class OrderCreate(BaseModel):
    car_id: int; client_id: int; employee_id: int
    open_date: date | None = None


class OrderUpdate(BaseModel):
    status: SoStatus | None = None     # open | in_progress | waiting_parts | done | cancelled
    close_date: date | None = None


class WorkCreate(BaseModel):
    description: str; hours: float; unit_price: float


@router.get("/")
async def list_orders(db: AsyncSession = Depends(get_db), _: TokenData = Depends(get_current_user)):
    return (await db.execute(select(ServiceOrder).order_by(ServiceOrder.open_date.desc()))).scalars().all()


@router.get("/works/all")
async def list_all_works(db: AsyncSession = Depends(get_db), _: TokenData = Depends(get_current_user)):
    """Все работы по всем нарядам одним запросом — избегаем N+1."""
    works = (await db.execute(select(ServiceWork).order_by(ServiceWork.service_order_id))).scalars().all()
    return [{"id": w.id, "service_order_id": w.service_order_id,
              "description": w.description, "hours": float(w.hours), "unit_price": float(w.unit_price)}
             for w in works]


@router.get("/{order_id}")
async def get_order(order_id: int, db: AsyncSession = Depends(get_db), _: TokenData = Depends(get_current_user)):
    o = await db.get(ServiceOrder, order_id)
    if not o:
        raise HTTPException(404)
    works = (await db.execute(
        select(ServiceWork).where(ServiceWork.service_order_id == order_id)
    )).scalars().all()
    d = {c.name: getattr(o, c.name) for c in ServiceOrder.__table__.columns}
    d["works"] = [{"id": w.id, "description": w.description, "hours": float(w.hours), "unit_price": float(w.unit_price)} for w in works]
    return d


@router.post("/", status_code=201)
async def create_order(
    body: OrderCreate,
    db: AsyncSession = Depends(get_db),
    user: TokenData = Depends(require_roles("master", "admin")),
):
    o = ServiceOrder(**body.model_dump(exclude_none=True))
    db.add(o)
    await db.commit()
    await db.refresh(o)
    db.add(AuditLog(user_role=user.role, user_name=user.name, entity="service_order",
                    action=AuditAction.create, record_id=o.id, status=AuditStatus.success,
                    details=f"Открыт наряд №{o.id}"))
    await db.commit()
    return o


@router.patch("/{order_id}")
async def update_order(
    order_id: int, body: OrderUpdate,
    db: AsyncSession = Depends(get_db),
    user: TokenData = Depends(require_roles("master", "admin")),
):
    o = await db.get(ServiceOrder, order_id)
    if not o:
        raise HTTPException(404)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(o, k, v)
    await db.commit()
    await db.refresh(o)
    return o


@router.post("/{order_id}/works", status_code=201)
async def add_work(
    order_id: int, body: WorkCreate,
    db: AsyncSession = Depends(get_db),
    user: TokenData = Depends(require_roles("master", "admin")),
):
    o = await db.get(ServiceOrder, order_id)
    if not o:
        raise HTTPException(404)
    w = ServiceWork(service_order_id=order_id, **body.model_dump())
    db.add(w)
    await db.commit()
    # Триггер пересчитал total — рефрешим наряд
    await db.refresh(o)
    await db.refresh(w)
    return {"work": w, "order_total": float(o.total)}


@router.delete("/{order_id}/works/{work_id}", status_code=204)
async def delete_work(
    order_id: int, work_id: int,
    db: AsyncSession = Depends(get_db),
    _: TokenData = Depends(require_roles("master", "admin")),
):
    w = await db.get(ServiceWork, work_id)
    if not w or w.service_order_id != order_id:
        raise HTTPException(404)
    await db.delete(w)
    await db.commit()
