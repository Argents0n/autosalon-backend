from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from auth import ROLE_PASSWORDS, TokenData, create_token, get_current_user
from database import get_db
from models import AuditLog, AuditAction, AuditStatus

router = APIRouter(prefix="/auth", tags=["auth"])

ROLE_NAMES = {
    "manager": "Петров П.П.",
    "master":  "Сидоров С.С.",
    "admin":   "Смирнова А.С.",
}


@router.post("/token")
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    role = form.username
    if role not in ROLE_PASSWORDS or form.password != ROLE_PASSWORDS[role]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверные учётные данные")

    name = ROLE_NAMES.get(role, role)
    token = create_token(role, name)

    db.add(AuditLog(user_role=role, user_name=name, entity="session",
                    action=AuditAction.login, status=AuditStatus.success,
                    details=f"Вход в систему ({role})"))
    await db.commit()

    return {"access_token": token, "token_type": "bearer", "role": role, "name": name}


@router.get("/me")
async def me(user: TokenData = Depends(get_current_user)):
    return user
