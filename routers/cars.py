from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from auth import TokenData, get_current_user, require_roles
from database import get_db
from models import Car, CarStatus, CarType, BodyType, Model, Brand

router = APIRouter(prefix="/cars", tags=["cars"])


class CarOut(BaseModel):
    id: int; model_id: int; vin: str; year: int; color: str
    mileage: int; price: float; status: CarStatus; type: CarType
    brand: str | None = None; model: str | None = None; body_type: str | None = None
    class Config: from_attributes = True


class CarCreate(BaseModel):
    model_id: int; vin: str; year: int; color: str
    mileage: int = 0; price: float; type: CarType


class CarUpdate(BaseModel):
    color: str | None = None; mileage: int | None = None
    price: float | None = None; status: CarStatus | None = None


@router.get("/", response_model=list[dict])
async def list_cars(
    status: CarStatus | None = None,
    db: AsyncSession = Depends(get_db),
    _: TokenData = Depends(get_current_user),
):
    q = (
        select(Car, Model.name.label("model_name"), Model.body_type,
               Brand.name.label("brand_name"))
        .join(Model, Car.model_id == Model.id)
        .join(Brand, Model.brand_id == Brand.id)
    )
    if status:
        q = q.where(Car.status == status)
    rows = (await db.execute(q)).all()
    result = []
    for car, model_name, body_type, brand_name in rows:
        d = {c.name: getattr(car, c.name) for c in Car.__table__.columns}
        d["model"] = model_name
        d["brand"] = brand_name
        d["body_type"] = str(body_type) if body_type else None
        result.append(d)
    return result


@router.get("/{car_id}")
async def get_car(car_id: int, db: AsyncSession = Depends(get_db), _: TokenData = Depends(get_current_user)):
    car = await db.get(Car, car_id)
    if not car:
        raise HTTPException(404, "Автомобиль не найден")
    return car


@router.post("/", status_code=201)
async def create_car(
    body: CarCreate,
    db: AsyncSession = Depends(get_db),
    user: TokenData = Depends(require_roles("admin")),
):
    car = Car(**body.model_dump())
    db.add(car)
    await db.commit()
    await db.refresh(car)
    return car


@router.patch("/{car_id}")
async def update_car(
    car_id: int, body: CarUpdate,
    db: AsyncSession = Depends(get_db),
    user: TokenData = Depends(require_roles("admin")),
):
    car = await db.get(Car, car_id)
    if not car:
        raise HTTPException(404, "Автомобиль не найден")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(car, k, v)
    await db.commit()
    await db.refresh(car)
    return car


@router.delete("/{car_id}", status_code=204)
async def delete_car(
    car_id: int,
    db: AsyncSession = Depends(get_db),
    _: TokenData = Depends(require_roles("admin")),
):
    car = await db.get(Car, car_id)
    if not car:
        raise HTTPException(404)
    await db.delete(car)
    await db.commit()
