"""Справочники: Brand, Model, Department, Employee."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from auth import TokenData, get_current_user, require_roles
from database import get_db
from models import Brand, Model, BodyType, Department, Employee

router = APIRouter(prefix="/refs", tags=["refs"])


# ── Brand ─────────────────────────────────────────────────────────────────────

class BrandCreate(BaseModel):
    name: str; country: str

@router.get("/brands")
async def list_brands(db: AsyncSession = Depends(get_db), _: TokenData = Depends(get_current_user)):
    return (await db.execute(select(Brand).order_by(Brand.name))).scalars().all()

@router.post("/brands", status_code=201)
async def create_brand(body: BrandCreate, db: AsyncSession = Depends(get_db),
                        _: TokenData = Depends(require_roles("admin"))):
    b = Brand(**body.model_dump())
    db.add(b); await db.commit(); await db.refresh(b); return b

@router.patch("/brands/{bid}")
async def update_brand(bid: int, body: BrandCreate, db: AsyncSession = Depends(get_db),
                        _: TokenData = Depends(require_roles("admin"))):
    b = await db.get(Brand, bid)
    if not b: raise HTTPException(404)
    b.name = body.name; b.country = body.country
    await db.commit(); await db.refresh(b); return b

@router.delete("/brands/{bid}", status_code=204)
async def delete_brand(bid: int, db: AsyncSession = Depends(get_db),
                        _: TokenData = Depends(require_roles("admin"))):
    b = await db.get(Brand, bid)
    if not b: raise HTTPException(404)
    await db.delete(b); await db.commit()


# ── Model ─────────────────────────────────────────────────────────────────────

class ModelCreate(BaseModel):
    brand_id: int; name: str; body_type: BodyType; car_class: str

@router.get("/models")
async def list_models(db: AsyncSession = Depends(get_db), _: TokenData = Depends(get_current_user)):
    return (await db.execute(select(Model).order_by(Model.name))).scalars().all()

@router.post("/models", status_code=201)
async def create_model(body: ModelCreate, db: AsyncSession = Depends(get_db),
                        _: TokenData = Depends(require_roles("admin"))):
    m = Model(**body.model_dump())
    db.add(m); await db.commit(); await db.refresh(m); return m

@router.delete("/models/{mid}", status_code=204)
async def delete_model(mid: int, db: AsyncSession = Depends(get_db),
                        _: TokenData = Depends(require_roles("admin"))):
    m = await db.get(Model, mid)
    if not m: raise HTTPException(404)
    await db.delete(m); await db.commit()


# ── Department ────────────────────────────────────────────────────────────────

class DeptCreate(BaseModel):
    name: str

@router.get("/departments")
async def list_depts(db: AsyncSession = Depends(get_db), _: TokenData = Depends(get_current_user)):
    return (await db.execute(select(Department))).scalars().all()

@router.post("/departments", status_code=201)
async def create_dept(body: DeptCreate, db: AsyncSession = Depends(get_db),
                       _: TokenData = Depends(require_roles("admin"))):
    d = Department(**body.model_dump())
    db.add(d); await db.commit(); await db.refresh(d); return d

@router.patch("/departments/{did}")
async def update_dept(did: int, body: DeptCreate, db: AsyncSession = Depends(get_db),
                       _: TokenData = Depends(require_roles("admin"))):
    d = await db.get(Department, did)
    if not d: raise HTTPException(404)
    d.name = body.name; await db.commit(); await db.refresh(d); return d

@router.delete("/departments/{did}", status_code=204)
async def delete_dept(did: int, db: AsyncSession = Depends(get_db),
                       _: TokenData = Depends(require_roles("admin"))):
    d = await db.get(Department, did)
    if not d: raise HTTPException(404)
    await db.delete(d); await db.commit()


# ── Employee ──────────────────────────────────────────────────────────────────

class EmpCreate(BaseModel):
    department_id: int; full_name: str; position: str
    phone: str | None = None; hire_date: date; is_active: bool = True

class EmpUpdate(BaseModel):
    department_id: int | None = None; full_name: str | None = None
    position: str | None = None; phone: str | None = None; is_active: bool | None = None

@router.get("/employees")
async def list_employees(db: AsyncSession = Depends(get_db), _: TokenData = Depends(get_current_user)):
    return (await db.execute(select(Employee).order_by(Employee.full_name))).scalars().all()

@router.post("/employees", status_code=201)
async def create_employee(body: EmpCreate, db: AsyncSession = Depends(get_db),
                           _: TokenData = Depends(require_roles("admin"))):
    e = Employee(**body.model_dump())
    db.add(e); await db.commit(); await db.refresh(e); return e

@router.patch("/employees/{eid}")
async def update_employee(eid: int, body: EmpUpdate, db: AsyncSession = Depends(get_db),
                           _: TokenData = Depends(require_roles("admin"))):
    e = await db.get(Employee, eid)
    if not e: raise HTTPException(404)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(e, k, v)
    await db.commit(); await db.refresh(e); return e

@router.delete("/employees/{eid}", status_code=204)
async def delete_employee(eid: int, db: AsyncSession = Depends(get_db),
                           _: TokenData = Depends(require_roles("admin"))):
    e = await db.get(Employee, eid)
    if not e: raise HTTPException(404)
    await db.delete(e); await db.commit()
