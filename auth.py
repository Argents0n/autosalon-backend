"""JWT-аутентификация. Пароли для ролей хранятся в .env."""
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from config import settings

Role = Literal["manager", "master", "admin"]

# Пароли указать в .env: MANAGER_PWD, MASTER_PWD, ADMIN_PWD
# По умолчанию — как в прототипе
import os
ROLE_PASSWORDS: dict[Role, str] = {
    "manager": os.getenv("MANAGER_PWD", "manager"),
    "master":  os.getenv("MASTER_PWD",  "master"),
    "admin":   os.getenv("ADMIN_PWD",   "admin123"),
}

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


class TokenData(BaseModel):
    role: Role
    name: str


def create_token(role: Role, name: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {"sub": role, "name": name, "exp": expire},
        settings.secret_key,
        algorithm=settings.algorithm,
    )


async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    exc = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный токен")
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        role = payload.get("sub")
        name = payload.get("name", "")
        if role not in ("manager", "master", "admin"):
            raise exc
        return TokenData(role=role, name=name)
    except JWTError:
        raise exc


def require_roles(*roles: Role):
    async def checker(user: TokenData = Depends(get_current_user)) -> TokenData:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Нет доступа")
        return user
    return checker
