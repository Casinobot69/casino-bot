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
    if user.get("approval_status") != "approved":
        raise HTTPException(status_code=403, detail="Hisobingiz tasdiqlanmagan")
    txs = await get_transactions(telegram_id=telegram_id, limit=5)
    return {"user": user, "recent_transactions": txs}


@router.get("/balance/{telegram_id}")
async def get_balance(telegram_id: int):
    user = await get_user(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    if user.get("is_banned"):
        raise HTTPException(status_code=403, detail="Bloklangan")
    if user.get("approval_status") != "approved":
        raise HTTPException(status_code=403, detail="Hisobingiz tasdiqlanmagan")
    return {"balance": user["balance"]}


@router.get("/transactions/{telegram_id}")
async def user_transactions(telegram_id: int, limit: int = 20):
    user = await get_user(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    if user.get("is_banned"):
        raise HTTPException(status_code=403, detail="Bloklangan")
    if user.get("approval_status") != "approved":
        raise HTTPException(status_code=403, detail="Hisobingiz tasdiqlanmagan")
    txs = await get_transactions(telegram_id=telegram_id, limit=limit)
    return {"transactions": txs}


class PromoRedeemRequest(BaseModel):
    telegram_id: int
    code: str


class WithdrawRequest(BaseModel):
    telegram_id: int
    amount: int
    details: str = ""


@router.post("/promo/redeem")
async def user_promo_redeem(body: PromoRedeemRequest):
    from backend.database import claim_promo
    user = await get_user(body.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    if user.get("is_banned"):
        raise HTTPException(status_code=403, detail="Bloklangan")
    if user.get("approval_status") != "approved":
        raise HTTPException(status_code=403, detail="Hisobingiz tasdiqlanmagan")
        
    success, msg = await claim_promo(body.telegram_id, body.code.upper().strip())
    if not success:
         raise HTTPException(status_code=400, detail=msg)
    user = await get_user(body.telegram_id)
    return {"success": True, "message": msg, "balance": user["balance"]}


@router.post("/withdraw")
async def user_withdraw_request(body: WithdrawRequest):
    from backend.database import create_withdrawal
    user = await get_user(body.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    if user.get("is_banned"):
        raise HTTPException(status_code=403, detail="Bloklangan")
    if user.get("approval_status") != "approved":
        raise HTTPException(status_code=403, detail="Hisobingiz tasdiqlanmagan")
        
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="Miqdor noto'g'ri")
    success, msg = await create_withdrawal(body.telegram_id, body.amount, body.details)
    if not success:
         raise HTTPException(status_code=400, detail=msg)
    user = await get_user(body.telegram_id)
    return {"success": True, "message": msg, "balance": user["balance"]}
