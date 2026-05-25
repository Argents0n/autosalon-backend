from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from auth import TokenData, get_current_user, require_roles
from database import get_db
from models import AuditLog, AuditAction, AuditStatus, TestDrive, TdResult

router = APIRouter(prefix="/test-drives", tags=["test_drives"])


class TdCreate(BaseModel):
    car_id: int; client_id: int; employee_id: int
    scheduled_at: datetime; duration_min: int | None = None; notes: str | None = None


class TdUpdate(BaseModel):
    result: TdResult | None = None; notes: str | None = None
    duration_min: int | None = None


@router.get("/")
async def list_tds(db: AsyncSession = Depends(get_db), _: TokenData = Depends(get_current_user)):
    return (await db.execute(select(TestDrive).order_by(TestDrive.scheduled_at.desc()))).scalars().all()


@router.post("/", status_code=201)
async def create_td(
    body: TdCreate,
    db: AsyncSession = Depends(get_db),
    user: TokenData = Depends(require_roles("manager", "admin")),
):
    td = TestDrive(**body.model_dump())
    db.add(td)
    try:
        await db.commit()
    except DBAPIError as e:
        await db.rollback()
        raise HTTPException(400, str(e.orig).split("\n")[0])
    await db.refresh(td)

    db.add(AuditLog(user_role=user.role, user_name=user.name, entity="test_drive",
                    action=AuditAction.create, record_id=td.id, status=AuditStatus.success,
                    details=f"Тест-драйв №{td.id} записан"))
    await db.commit()
    return td


@router.patch("/{td_id}")
async def update_td(
    td_id: int, body: TdUpdate,
    db: AsyncSession = Depends(get_db),
    user: TokenData = Depends(require_roles("manager", "admin")),
):
    td = await db.get(TestDrive, td_id)
    if not td:
        raise HTTPException(404)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(td, k, v)
    try:
        await db.commit()
    except DBAPIError as e:
        await db.rollback()
        raise HTTPException(400, str(e.orig).split("\n")[0])
    await db.refresh(td)
    return td


@router.delete("/{td_id}", status_code=204)
async def delete_td(
    td_id: int,
    db: AsyncSession = Depends(get_db),
    _: TokenData = Depends(require_roles("manager", "admin")),
):
    td = await db.get(TestDrive, td_id)
    if not td:
        raise HTTPException(404)
    await db.delete(td)
    await db.commit()
