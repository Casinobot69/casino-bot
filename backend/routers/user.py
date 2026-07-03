from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.database import get_user, create_or_update_user, get_transactions, update_balance

router = APIRouter(prefix="/api/user", tags=["user"])


class RegisterRequest(BaseModel):
    telegram_id: int
    username: str = ""
    first_name: str = ""
    last_name: str = ""
    photo_url: str = ""


class DepositRequest(BaseModel):
    telegram_id: int
    amount: int
    payment_id: str = ""


@router.post("/register")
async def register(body: RegisterRequest):
    user = await create_or_update_user(
        telegram_id=body.telegram_id,
        username=body.username,
        first_name=body.first_name,
        last_name=body.last_name,
        photo_url=body.photo_url,
    )
    return {"success": True, "user": user}


@router.get("/profile/{telegram_id}")
async def get_profile(telegram_id: int):
    user = await get_user(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    if user.get("is_banned"):
        raise HTTPException(status_code=403, detail="Bloklangan")
    txs = await get_transactions(telegram_id=telegram_id, limit=5)
    return {"user": user, "recent_transactions": txs}


@router.get("/balance/{telegram_id}")
async def get_balance(telegram_id: int):
    user = await get_user(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    return {"balance": user["balance"]}


@router.get("/transactions/{telegram_id}")
async def user_transactions(telegram_id: int, limit: int = 20):
    user = await get_user(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    txs = await get_transactions(telegram_id=telegram_id, limit=limit)
    return {"transactions": txs}
