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


@router.post("/users/{telegram_id}/approve")
async def approve_user(telegram_id: int, token: str = Header(alias="X-Admin-Token")):
    verify_admin(token)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET approval_status='approved' WHERE telegram_id=?", (telegram_id,))
        await db.commit()
    
    try:
        from bot.main import bot
        await bot.send_message(
            telegram_id,
            "🎉 <b>Tabriklaymiz!</b>\n\nSizning o'yinga kirish so'rovingiz admin tomonidan tasdiqlandi. "
            "Endi botdan va o'yin xonalaridan to'liq foydalanishingiz mumkin!",
            parse_mode="HTML"
        )
    except Exception:
        pass
    return {"success": True, "message": "Foydalanuvchi tasdiqlandi"}


@router.post("/users/{telegram_id}/reject")
async def reject_user(telegram_id: int, token: str = Header(alias="X-Admin-Token")):
    verify_admin(token)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET approval_status='rejected' WHERE telegram_id=?", (telegram_id,))
        await db.commit()
        
    try:
        from bot.main import bot
        await bot.send_message(
            telegram_id,
            "❌ <b>Tizimga kirish so'rovi</b>\n\nAfsuski, sizning kirish so'rovingiz admin tomonidan rad etildi.",
            parse_mode="HTML"
        )
    except Exception:
        pass
    return {"success": True, "message": "Foydalanuvchi rad etildi"}


class PromoCreate(BaseModel):
    code: str
    reward: int
    max_uses: int = 1


class FakePlayerRequest(BaseModel):
    room_id: str
    username: str = ""
    first_name: str = ""
    bet: int = 100


@router.get("/promos")
async def admin_get_promos(token: str = Header(alias="X-Admin-Token")):
    verify_admin(token)
    from backend.database import get_promos
    return {"promos": await get_promos()}


@router.post("/promos")
async def admin_create_promo(body: PromoCreate, token: str = Header(alias="X-Admin-Token")):
    verify_admin(token)
    from backend.database import create_promo
    success = await create_promo(body.code.upper().strip(), body.reward, body.max_uses)
    if not success:
        raise HTTPException(status_code=400, detail="Promo-kod yaratib bo'lmadi (ehtimol allaqachon mavjud)")
    return {"success": True}


@router.delete("/promos/{promo_id}")
async def admin_delete_promo(promo_id: int, token: str = Header(alias="X-Admin-Token")):
    verify_admin(token)
    from backend.database import delete_promo
    await delete_promo(promo_id)
    return {"success": True}


@router.get("/withdrawals")
async def admin_get_withdrawals(token: str = Header(alias="X-Admin-Token"), status: Optional[str] = None):
    verify_admin(token)
    from backend.database import get_withdrawals
    return {"withdrawals": await get_withdrawals(status)}


@router.post("/withdrawals/{withdrawal_id}/{action}")
async def admin_process_withdrawal(withdrawal_id: int, action: str, token: str = Header(alias="X-Admin-Token")):
    verify_admin(token)
    if action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Noto'g'ri amal")
    from backend.database import process_withdrawal
    success, msg = await process_withdrawal(withdrawal_id, action)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}


@router.get("/audit")
async def admin_get_audit(token: str = Header(alias="X-Admin-Token"), limit: int = 100):
    verify_admin(token)
    from backend.database import get_audit_logs
    return {"logs": await get_audit_logs(limit)}


@router.get("/rooms")
async def admin_get_rooms(token: str = Header(alias="X-Admin-Token")):
    verify_admin(token)
    from backend.game_logic import active_rooms
    rooms = []
    for r_id, room in active_rooms.items():
        rooms.append({
            "room_id": room.room_id,
            "status": room.status,
            "total_bank": room.get_total_bank(),
            "time_left": room.time_left,
            "players_count": len(room.players),
            "players": room.players
        })
    return {"rooms": rooms}


@router.post("/rooms/{room_id}/spin")
async def admin_force_spin(room_id: str, token: str = Header(alias="X-Admin-Token")):
    verify_admin(token)
    from backend.game_logic import active_rooms, _spin_game
    from backend.database import get_setting
    room = active_rooms.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Xona topilmadi")
    if room.status not in ("waiting", "betting"):
        raise HTTPException(status_code=400, detail="Xonani aylantirib bo'lmaydi (ehtimol aylanmoqda)")
    if len(room.players) < 2:
        raise HTTPException(status_code=400, detail="Kamida 2 ta o'yinchi bo'lishi kerak")
    
    import asyncio
    asyncio.create_task(_spin_game(room_id, int(await get_setting("commission_rate") or 5)))
    return {"success": True, "message": "O'yin aylantirildi"}


@router.post("/fake-player")
async def admin_inject_fake(body: FakePlayerRequest, token: str = Header(alias="X-Admin-Token")):
    verify_admin(token)
    from backend.game_logic import active_rooms, join_game_room
    import random
    room = active_rooms.get(body.room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Xona topilmadi")
    
    fake_tg_id = random.randint(1000000, 9999999)
    fake_user = {
        "id": fake_tg_id,
        "telegram_id": fake_tg_id,
        "username": body.username or f"player_{random.randint(100, 999)}",
        "first_name": body.first_name or f"Bot_{random.randint(1, 50)}",
        "last_name": "",
        "photo_url": ""
    }
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (telegram_id, username, first_name, last_name, balance) VALUES (?,?,?,?,?)",
            (fake_tg_id, fake_user["username"], fake_user["first_name"], "", 10000)
        )
        await db.commit()
        async with db.execute("SELECT id FROM users WHERE telegram_id=?", (fake_tg_id,)) as c:
            row = await c.fetchone()
            if row:
                fake_user["id"] = row[0]
                
    success, msg = await join_game_room(body.room_id, fake_user, body.bet)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    
    from backend.game_logic import manager
    await manager.broadcast(body.room_id, {
        "action": "player_joined",
        "players": room.players,
        "total_bank": room.get_total_bank(),
        "status": room.status,
        "time_left": room.time_left,
        "room_id": room.room_id
    })
    
    return {"success": True, "message": "Fake o'yinchi qo'shildi"}
