from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from auth import TokenData, get_current_user, require_roles
from database import get_db
from models import Client

router = APIRouter(prefix="/clients", tags=["clients"])


class ClientCreate(BaseModel):
    full_name: str; phone: str
    email: str | None = None; passport: str | None = None; birth_date: date | None = None


class ClientUpdate(BaseModel):
    full_name: str | None = None; phone: str | None = None
    email: str | None = None; passport: str | None = None; birth_date: date | None = None


@router.get("/")
async def list_clients(db: AsyncSession = Depends(get_db), _: TokenData = Depends(get_current_user)):
    return (await db.execute(select(Client).order_by(Client.full_name))).scalars().all()


@router.get("/{client_id}")
async def get_client(client_id: int, db: AsyncSession = Depends(get_db), _: TokenData = Depends(get_current_user)):
    c = await db.get(Client, client_id)
    if not c:
        raise HTTPException(404, "Клиент не найден")
    return c


@router.post("/", status_code=201)
async def create_client(
    body: ClientCreate,
    db: AsyncSession = Depends(get_db),
    _: TokenData = Depends(require_roles("manager", "master", "admin")),
):
    c = Client(**body.model_dump())
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


@router.patch("/{client_id}")
async def update_client(
    client_id: int, body: ClientUpdate,
    db: AsyncSession = Depends(get_db),
    _: TokenData = Depends(require_roles("manager", "master", "admin")),
):
    c = await db.get(Client, client_id)
    if not c:
        raise HTTPException(404)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(c, k, v)
    await db.commit()
    await db.refresh(c)
    return c
