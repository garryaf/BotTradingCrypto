from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..auth.dependencies import get_current_admin
from ..db import get_session
from ..models import BinanceCredential, User

router = APIRouter(prefix="/api/v1/admin")

VALID_ROLES = {"user", "admin"}


class UserPatch(BaseModel):
    role: str | None = None
    is_active: bool | None = None


@router.get("/users")
async def list_users(admin: User = Depends(get_current_admin), session: AsyncSession = Depends(get_session)):
    users = (await session.exec(select(User).order_by(User.created_at))).all()
    configured_ids = set((await session.exec(select(BinanceCredential.user_id))).all())
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "binance_configured": u.id in configured_ids,
            "created_at": u.created_at,
        }
        for u in users
    ]


@router.patch("/users/{user_id}")
async def update_user(
    user_id: UUID,
    body: UserPatch,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    target = await session.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if str(target.id) == str(admin.id) and (body.role == "user" or body.is_active is False):
        raise HTTPException(status_code=400, detail="Can't demote or disable your own account")

    if body.role is not None:
        if body.role not in VALID_ROLES:
            raise HTTPException(status_code=422, detail=f"role must be one of {VALID_ROLES}")
        target.role = body.role
    if body.is_active is not None:
        target.is_active = body.is_active

    await session.commit()
    return {"id": str(target.id), "email": target.email, "role": target.role, "is_active": target.is_active}
