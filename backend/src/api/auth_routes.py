from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..auth.dependencies import get_current_user
from ..auth.security import (
    COOKIE_NAME,
    create_access_token,
    decrypt_secret,
    encrypt_secret,
    hash_password,
    verify_password,
)
from ..db import get_session
from ..models import BinanceCredential, User

router = APIRouter(prefix="/api/v1/auth")

COOKIE_MAX_AGE_SEC = 7 * 24 * 3600


class Credentials(BaseModel):
    email: str
    password: str


class BinanceCredentialsIn(BaseModel):
    api_key: str
    api_secret: str


def _set_session_cookie(response: Response, user_id) -> None:
    response.set_cookie(
        COOKIE_NAME,
        create_access_token(user_id),
        max_age=COOKIE_MAX_AGE_SEC,
        httponly=True,
        samesite="lax",
    )


@router.post("/register")
async def register(body: Credentials, response: Response, session: AsyncSession = Depends(get_session)):
    existing = (await session.exec(select(User).where(User.email == body.email))).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    is_first_user = (await session.exec(select(User))).first() is None
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        role="admin" if is_first_user else "user",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    _set_session_cookie(response, user.id)
    return {"email": user.email, "role": user.role}


@router.post("/login")
async def login(body: Credentials, response: Response, session: AsyncSession = Depends(get_session)):
    user = (await session.exec(select(User).where(User.email == body.email))).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    _set_session_cookie(response, user.id)
    return {"email": user.email, "role": user.role}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {"email": user.email, "role": user.role}


@router.get("/binance-credentials")
async def get_binance_credentials(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
):
    cred = (await session.exec(select(BinanceCredential).where(BinanceCredential.user_id == user.id))).first()
    if not cred:
        return {"configured": False, "api_key_last4": None}
    return {"configured": True, "api_key_last4": decrypt_secret(cred.api_key_encrypted)[-4:]}


@router.put("/binance-credentials")
async def put_binance_credentials(
    body: BinanceCredentialsIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    cred = (await session.exec(select(BinanceCredential).where(BinanceCredential.user_id == user.id))).first()
    if cred:
        cred.api_key_encrypted = encrypt_secret(body.api_key)
        cred.api_secret_encrypted = encrypt_secret(body.api_secret)
        cred.updated_at = datetime.now(timezone.utc)
    else:
        session.add(
            BinanceCredential(
                user_id=user.id,
                api_key_encrypted=encrypt_secret(body.api_key),
                api_secret_encrypted=encrypt_secret(body.api_secret),
            )
        )
    await session.commit()
    return {"configured": True, "api_key_last4": body.api_key[-4:]}
