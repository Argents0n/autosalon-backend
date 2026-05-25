from fastapi import APIRouter, Depends
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from auth import TokenData, get_current_user
from database import get_db
from models import AuditLog, Employee, ServiceOrder

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/sales")
async def sales_report(
    date_from: date = date(2025, 1, 1),
    date_to: date = date(2025, 12, 31),
    db: AsyncSession = Depends(get_db),
    _: TokenData = Depends(get_current_user),
):
    """KPI менеджеров через fn_employee_sales_summary()."""
    managers = (await db.execute(
        select(Employee).where(
            Employee.is_active.is_(True),
            Employee.position.ilike("%менеджер%"),
        )
    )).scalars().all()

    result = []
    for emp in managers:
        row = (await db.execute(
            text("SELECT * FROM fn_employee_sales_summary(:eid, :dfrom, :dto)"),
            {"eid": emp.id, "dfrom": date_from, "dto": date_to},
        )).mappings().first()
        result.append({
            "id": emp.id,
            "full_name": emp.full_name,
            "position": emp.position,
            **dict(row),
        })
    return result


@router.get("/service-open")
async def service_open_report(
    db: AsyncSession = Depends(get_db),
    _: TokenData = Depends(get_current_user),
):
    """Открытые заказ-наряды с длительностью через fn_service_order_duration()."""
    orders = (await db.execute(
        select(ServiceOrder).where(
            ServiceOrder.status.notin_(["done", "cancelled"])
        ).order_by(ServiceOrder.open_date)
    )).scalars().all()

    result = []
    for o in orders:
        dur = (await db.execute(
            text("SELECT fn_service_order_duration(:oid)"), {"oid": o.id}
        )).scalar()
        d = {c.name: getattr(o, c.name) for c in ServiceOrder.__table__.columns}
        d["duration_days"] = dur
        result.append(d)
    return result


@router.get("/audit")
async def audit_log(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _: TokenData = Depends(get_current_user),
):
    logs = (await db.execute(
        select(AuditLog).order_by(AuditLog.ts.desc()).limit(limit)
    )).scalars().all()
    return logs
