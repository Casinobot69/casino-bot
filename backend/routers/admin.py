import os
from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel
from typing import Optional
import aiosqlite
from backend.database import (
    get_all_users, get_user, update_balance, get_stats,
    get_all_settings, set_setting, get_transactions, get_game_history, DB_PATH
)

router = APIRouter(prefix="/api/admin", tags=["admin"])

ADMIN_SECRET = os.getenv("ADMIN_SECRET", "supersecretadmintoken2024")

def verify_admin(x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token")):
    # Try alternate alias casing if the default one is empty due to FastAPI header conversion
    token = x_admin_token
    if not token:
        raise HTTPException(status_code=401, detail="X-Admin-Token header missing")
    if token != ADMIN_SECRET:
        raise HTTPException(status_code=401, detail="Token noto'g'ri")
    return True


class BalanceAction(BaseModel):
    telegram_id: int
    amount: int
    description: Optional[str] = ""

class AdminAction(BaseModel):
    telegram_id: int

class BanAction(BaseModel):
    telegram_id: int
    reason: Optional[str] = ""

class BroadcastMessage(BaseModel):
    message: str

class SettingUpdate(BaseModel):
    key: str
    value: str

class AdminMessage(BaseModel):
    telegram_id: int
    message: str


@router.get("/stats")
async def admin_stats(token: str = Header(alias="X-Admin-Token")):
    verify_admin(token)
    return await get_stats()


@router.get("/users")
async def admin_users(
    token: str = Header(alias="X-Admin-Token"),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    search: str = Query("")
):
    verify_admin(token)
    users = await get_all_users(limit=limit, offset=offset, search=search)
    return {"users": users, "total": len(users)}


@router.get("/user/{telegram_id}")
async def admin_get_user(telegram_id: int, token: str = Header(alias="X-Admin-Token")):
    verify_admin(token)
    user = await get_user(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    txs = await get_transactions(telegram_id=telegram_id, limit=10)
    return {"user": user, "transactions": txs}


@router.post("/balance/add")
async def admin_add_balance(body: BalanceAction, token: str = Header(alias="X-Admin-Token")):
    verify_admin(token)
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="Miqdor musbat bo'lishi kerak")
    user = await get_user(body.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    updated = await update_balance(body.telegram_id, body.amount, "admin_add",
                                   body.description or f"Admin qo'shdi: +{body.amount}")
    # Notify user
    try:
        from bot.main import bot
        await bot.send_message(
            body.telegram_id,
            f"💰 <b>Balansingiz to'ldirildi!</b>\n\n"
            f"➕ Qo'shildi: ⭐ {body.amount:,}\n"
            f"💼 Joriy balans: ⭐ {updated['balance']:,}",
            parse_mode="HTML"
        )
    except Exception:
        pass
    return {"success": True, "balance": updated["balance"]}


@router.post("/balance/remove")
async def admin_remove_balance(body: BalanceAction, token: str = Header(alias="X-Admin-Token")):
    verify_admin(token)
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="Miqdor musbat bo'lishi kerak")
    user = await get_user(body.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    if user["balance"] < body.amount:
        raise HTTPException(status_code=400, detail="Foydalanuvchi balansi yetarli emas")
    updated = await update_balance(body.telegram_id, -body.amount, "admin_remove",
                                   body.description or f"Admin ayirdi: -{body.amount}")
    try:
        from bot.main import bot
        await bot.send_message(
            body.telegram_id,
            f"💸 <b>Balansingizdan ayirildi</b>\n\n"
            f"➖ Ayirildi: ⭐ {body.amount:,}\n"
            f"💼 Joriy balans: ⭐ {updated['balance']:,}",
            parse_mode="HTML"
        )
    except Exception:
        pass
    return {"success": True, "balance": updated["balance"]}


@router.post("/admin/grant")
async def admin_grant(body: AdminAction, token: str = Header(alias="X-Admin-Token")):
    verify_admin(token)
    user = await get_user(body.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_admin=1 WHERE telegram_id=?", (body.telegram_id,))
        await db.commit()
    try:
        from bot.main import bot
        await bot.send_message(body.telegram_id, "👑 Sizga <b>Admin</b> huquqi berildi!", parse_mode="HTML")
    except Exception:
        pass
    return {"success": True}


@router.post("/admin/revoke")
async def admin_revoke(body: AdminAction, token: str = Header(alias="X-Admin-Token")):
    verify_admin(token)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_admin=0 WHERE telegram_id=?", (body.telegram_id,))
        await db.commit()
    return {"success": True}


@router.post("/ban")
async def admin_ban(body: BanAction, token: str = Header(alias="X-Admin-Token")):
    verify_admin(token)
    user = await get_user(body.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned=1 WHERE telegram_id=?", (body.telegram_id,))
        await db.commit()
    try:
        from bot.main import bot
        reason_str = body.reason or "Ko'rsatilmagan"
        await bot.send_message(
            body.telegram_id,
            f"🚫 <b>Hisobingiz bloklandi</b>\n\n"
            f"Sabab: {reason_str}\n\n"
            f"Murojaat uchun: admin bilan bog'laning",
            parse_mode="HTML"
        )
    except Exception:
        pass
    return {"success": True}


@router.post("/unban")
async def admin_unban(body: BanAction, token: str = Header(alias="X-Admin-Token")):
    verify_admin(token)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned=0 WHERE telegram_id=?", (body.telegram_id,))
        await db.commit()
    try:
        from bot.main import bot
        await bot.send_message(
            body.telegram_id,
            "✅ <b>Hisobingiz tiklandi!</b>\n\nEndi botdan foydalanishingiz mumkin.",
            parse_mode="HTML"
        )
    except Exception:
        pass
    return {"success": True}


@router.post("/broadcast")
async def admin_broadcast(body: BroadcastMessage, token: str = Header(alias="X-Admin-Token")):
    verify_admin(token)
    users = await get_all_users(limit=10000)
    sent = 0
    failed = 0
    try:
        from bot.main import bot
        for user in users:
            if user.get("is_banned"):
                continue
            try:
                await bot.send_message(
                    user["telegram_id"],
                    f"📢 <b>Xabar</b>\n\n{body.message}",
                    parse_mode="HTML"
                )
                sent += 1
            except Exception:
                failed += 1
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    # Log message
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO messages (from_admin, message, sent_count) VALUES (1, ?, ?)", (body.message, sent))
        await db.commit()
    return {"success": True, "sent": sent, "failed": failed}


@router.post("/message")
async def admin_send_message(body: AdminMessage, token: str = Header(alias="X-Admin-Token")):
    verify_admin(token)
    try:
        from bot.main import bot
        await bot.send_message(
            body.telegram_id,
            f"💬 <b>Admin xabari:</b>\n\n{body.message}",
            parse_mode="HTML"
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/settings")
async def admin_get_settings(token: str = Header(alias="X-Admin-Token")):
    verify_admin(token)
    return await get_all_settings()


@router.post("/settings")
async def admin_update_setting(body: SettingUpdate, token: str = Header(alias="X-Admin-Token")):
    verify_admin(token)
    await set_setting(body.key, body.value)
    return {"success": True, "key": body.key, "value": body.value}


@router.get("/transactions")
async def admin_transactions(
    token: str = Header(alias="X-Admin-Token"),
    limit: int = Query(50, le=200)
):
    verify_admin(token)
    txs = await get_transactions(limit=limit)
    return {"transactions": txs}


@router.get("/games")
async def admin_games(token: str = Header(alias="X-Admin-Token"), limit: int = Query(50)):
    verify_admin(token)
    games = await get_game_history(limit=limit)
    return {"games": games}


@router.delete("/user/{telegram_id}")
async def admin_delete_user(telegram_id: int, token: str = Header(alias="X-Admin-Token")):
    verify_admin(token)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM users WHERE telegram_id=?", (telegram_id,))
        await db.commit()
    return {"success": True}


@router.post("/verify")
async def admin_verify(token: str = Header(alias="X-Admin-Token")):
    verify_admin(token)
    return {"success": True, "message": "Token to'g'ri"}
