import asyncio
import hashlib
import json
import os
import random
import secrets
import time
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import WebSocket
import aiosqlite

DB_PATH = os.getenv("DB_PATH", "casino.db")

PLAYER_COLORS = [
    "#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A",
    "#C3A6FF", "#FFD93D", "#6BCB77", "#FF8CC8",
    "#A8E6CF", "#FF7F7F",
]

class ConnectionManager:
    def __init__(self):
        self.rooms: Dict[str, Dict] = {}           # room_id -> room data
        self.connections: Dict[str, List[WebSocket]] = {}  # room_id -> [ws]
        self.user_ws: Dict[int, WebSocket] = {}    # telegram_id -> ws (for notifications)

    async def connect(self, websocket: WebSocket, room_id: str, telegram_id: int):
        await websocket.accept()
        if room_id not in self.connections:
            self.connections[room_id] = []
        self.connections[room_id].append(websocket)
        self.user_ws[telegram_id] = websocket

    def disconnect(self, websocket: WebSocket, room_id: str, telegram_id: int):
        if room_id in self.connections:
            if websocket in self.connections[room_id]:
                self.connections[room_id].remove(websocket)
        if telegram_id in self.user_ws:
            del self.user_ws[telegram_id]

    async def broadcast(self, room_id: str, message: dict):
        if room_id in self.connections:
            dead = []
            for ws in self.connections[room_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.connections[room_id].remove(ws)

    async def send_to_user(self, telegram_id: int, message: dict):
        ws = self.user_ws.get(telegram_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()


class GameRoom:
    def __init__(self, room_id: str, creator_id: int):
        self.room_id = room_id
        self.creator_id = creator_id
        self.players: List[dict] = []
        self.status = "waiting"      # waiting | betting | spinning | finished
        self.timer_task: Optional[asyncio.Task] = None
        self.timer_seconds = 30
        self.time_left = 30
        self.game_db_id: Optional[int] = None
        self.game_hash = secrets.token_hex(16)

    def get_total_bank(self):
        return sum(p["bet"] for p in self.players)

    def get_player(self, telegram_id: int):
        return next((p for p in self.players if p["telegram_id"] == telegram_id), None)

    def has_player(self, telegram_id: int):
        return any(p["telegram_id"] == telegram_id for p in self.players)

    def to_dict(self):
        total = self.get_total_bank()
        players = []
        for p in self.players:
            chance = (p["bet"] / total * 100) if total > 0 else 0
            players.append({**p, "chance": round(chance, 2)})
        return {
            "room_id": self.room_id,
            "status": self.status,
            "players": players,
            "total_bank": total,
            "time_left": self.time_left,
            "game_hash": self.game_hash,
        }


# Active rooms in memory
active_rooms: Dict[str, GameRoom] = {}


async def create_game_room(telegram_id: int, commission_rate: int = 5, timer: int = 30) -> GameRoom:
    room_id = f"game_{int(time.time())}_{random.randint(1000, 9999)}"
    room = GameRoom(room_id, telegram_id)
    room.timer_seconds = timer
    room.time_left = timer
    active_rooms[room_id] = room

    # Save to DB
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO games (room_id, status, game_hash) VALUES (?, 'waiting', ?)",
            (room_id, room.game_hash)
        )
        room.game_db_id = cursor.lastrowid
        await db.commit()

    return room


async def join_game_room(room_id: str, user: dict, bet: int) -> tuple[bool, str]:
    room = active_rooms.get(room_id)
    if not room:
        return False, "Xona topilmadi"
    if room.status not in ("waiting", "betting"):
        return False, "O'yin allaqachon boshlangan"

    settings = await _get_settings()
    max_players = int(settings.get("max_players", 8))
    min_bet = int(settings.get("min_bet", 100))
    max_bet = int(settings.get("max_bet", 2500))

    if len(room.players) >= max_players:
        return False, f"Xona to'liq ({max_players} o'yinchi)"
    if bet < min_bet or bet > max_bet:
        return False, f"Stavka {min_bet}-{max_bet} orasida bo'lishi kerak"
    if room.has_player(user["telegram_id"]):
        return False, "Siz allaqachon xonada turibsiz"

    # Deduct balance
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT balance FROM users WHERE telegram_id=?", (user["telegram_id"],)) as c:
                row = await c.fetchone()
                if not row or row[0] < bet:
                    return False, "Balansingiz yetarli emas"
            await db.execute("UPDATE users SET balance=balance-? WHERE telegram_id=?", (bet, user["telegram_id"]))
            await db.execute(
                """INSERT INTO transactions (user_id, telegram_id, type, amount, description, balance_before, balance_after)
                   VALUES (?, ?, 'game_bet', ?, ?, ?, ?)""",
                (user["id"], user["telegram_id"], -bet, f"O'yin #{room_id} stavka",
                 row[0], row[0] - bet)
            )
            await db.commit()
    except Exception as e:
        return False, str(e)

    color = PLAYER_COLORS[len(room.players) % len(PLAYER_COLORS)]
    initials = (user.get("first_name", "?")[:1] + user.get("last_name", "")[:1]).upper() or "?"

    room.players.append({
        "telegram_id": user["telegram_id"],
        "username": user.get("username", ""),
        "first_name": user.get("first_name", ""),
        "initials": initials,
        "photo_url": user.get("photo_url", ""),
        "bet": bet,
        "color": color,
    })

    # Save to DB
    if room.game_db_id:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO game_players (game_id, user_id, telegram_id, username, first_name, bet_amount) VALUES (?,?,?,?,?,?)",
                (room.game_db_id, user["id"], user["telegram_id"], user.get("username",""), user.get("first_name",""), bet)
            )
            await db.execute("UPDATE games SET total_bank=? WHERE id=?", (room.get_total_bank(), room.game_db_id))
            await db.commit()

    # Start timer if 2+ players
    if len(room.players) >= 2 and room.status == "waiting":
        room.status = "betting"
        asyncio.create_task(run_game_timer(room_id))

    return True, "OK"


async def run_game_timer(room_id: str):
    room = active_rooms.get(room_id)
    if not room:
        return

    settings = await _get_settings()
    commission_rate = int(settings.get("commission_rate", 5))

    room.time_left = room.timer_seconds
    while room.time_left > 0 and room.status == "betting":
        await manager.broadcast(room_id, {
            "action": "timer",
            "time_left": room.time_left,
            **room.to_dict()
        })
        await asyncio.sleep(1)
        room.time_left -= 1

    if room.status == "betting" and len(room.players) >= 2:
        await _spin_game(room_id, commission_rate)


async def _spin_game(room_id: str, commission_rate: int = 5):
    from backend.database import NFT_PRIZES
    room = active_rooms.get(room_id)
    if not room or len(room.players) < 2:
        return

    room.status = "spinning"
    total_bank = room.get_total_bank()

    # Weighted random winner
    weights = [p["bet"] for p in room.players]
    winner = random.choices(room.players, weights=weights, k=1)[0]

    # Commission
    commission = int(total_bank * commission_rate / 100)
    winner_amount = total_bank - commission

    # Calculate spin angle for winner's sector
    winner_idx = room.players.index(winner)
    # Calculate cumulative angles
    cumulative = 0
    sector_start = 0
    for i, p in enumerate(room.players):
        sector_angle = p["bet"] / total_bank * 360
        if i == winner_idx:
            sector_start = cumulative + sector_angle / 2
        cumulative += sector_angle
    # The pointer is at top (0 degrees). Winner angle = 360 - sector_start
    target_angle = (360 - sector_start) % 360

    # Broadcast spin start
    await manager.broadcast(room_id, {
        "action": "spin_start",
        "winner_telegram_id": winner["telegram_id"],
        "target_angle": target_angle,
        "spin_duration": 5000,
        **room.to_dict()
    })

    await asyncio.sleep(5.5)  # Wait for animation

    # Credit winner
    async with aiosqlite.connect(DB_PATH) as db:
        # Get winner's current balance
        async with db.execute("SELECT balance, id FROM users WHERE telegram_id=?", (winner["telegram_id"],)) as c:
            w_row = await c.fetchone()

        await db.execute(
            "UPDATE users SET balance=balance+?, total_wins=total_wins+1 WHERE telegram_id=?",
            (winner_amount, winner["telegram_id"])
        )
        # Update stats for all players
        for p in room.players:
            await db.execute(
                "UPDATE users SET total_games=total_games+1, total_wagered=total_wagered+? WHERE telegram_id=?",
                (p["bet"], p["telegram_id"])
            )
        await db.execute(
            "UPDATE users SET total_won=total_won+? WHERE telegram_id=?",
            (winner_amount, winner["telegram_id"])
        )

        # Transaction for winner
        balance_now = (w_row[0] if w_row else 0) + winner_amount
        await db.execute(
            """INSERT INTO transactions (user_id, telegram_id, type, amount, description, balance_before, balance_after)
               VALUES (?, ?, 'game_win', ?, ?, ?, ?)""",
            (w_row[1] if w_row else 0, winner["telegram_id"], winner_amount,
             f"O'yin #{room_id} g'alaba", balance_now - winner_amount, balance_now)
        )

        # Commission to admin
        admin_ids = [int(x) for x in os.getenv("ADMIN_IDS", "6594366391").split(",")]
        for admin_id in admin_ids:
            async with db.execute("SELECT id, balance FROM users WHERE telegram_id=?", (admin_id,)) as c:
                a_row = await c.fetchone()
            if a_row and commission > 0:
                await db.execute("UPDATE users SET balance=balance+? WHERE telegram_id=?", (commission, admin_id))
                await db.execute(
                    """INSERT INTO transactions (user_id, telegram_id, type, amount, description, balance_before, balance_after)
                       VALUES (?, ?, 'commission', ?, ?, ?, ?)""",
                    (a_row[0], admin_id, commission, f"Komissiya o'yin #{room_id}",
                     a_row[1], a_row[1] + commission)
                )

        # Update game in DB
        nft_prize = None
        for nft in sorted(NFT_PRIZES, key=lambda x: -x["price"]):
            if winner_amount >= nft["price"]:
                nft_prize = json.dumps({"name": nft["name"], "emoji": nft["emoji"], "price": nft["price"]})
                break

        await db.execute(
            """UPDATE games SET status='finished', commission=?, winner_telegram_id=?,
               winner_amount=?, nft_prize=?, finished_at=CURRENT_TIMESTAMP,
               total_bank=? WHERE id=?""",
            (commission, winner["telegram_id"], winner_amount, nft_prize, total_bank, room.game_db_id)
        )
        # Update game_players chances
        for p in room.players:
            chance = p["bet"] / total_bank * 100
            is_w = 1 if p["telegram_id"] == winner["telegram_id"] else 0
            await db.execute(
                "UPDATE game_players SET chance=?, is_winner=? WHERE game_id=? AND telegram_id=?",
                (round(chance, 2), is_w, room.game_db_id, p["telegram_id"])
            )
        await db.commit()

    nft_data = json.loads(nft_prize) if nft_prize else None
    room.status = "finished"

    await manager.broadcast(room_id, {
        "action": "game_over",
        "winner": winner,
        "winner_amount": winner_amount,
        "commission": commission,
        "nft_prize": nft_data,
        "game_hash": room.game_hash,
        **room.to_dict()
    })

    # Notify via bot
    try:
        from bot.main import bot
        for p in room.players:
            if p["telegram_id"] == winner["telegram_id"]:
                nft_text = ""
                if nft_data:
                    nft_text = f"\n\n🎁 <b>NFT Sovg'a qo'lga kiritdi:</b> {nft_data['emoji']} {nft_data['name']} (⭐ {nft_data['price']:,})"
                await bot.send_message(
                    p["telegram_id"],
                    f"🏆 <b>G'ALABA!</b>\n\n"
                    f"🎮 O'yin: <code>#{room_id[-6:]}</code>\n"
                    f"💰 Bank: ⭐ {total_bank:,}\n"
                    f"🎁 G'alaba: ⭐ {winner_amount:,}\n"
                    f"🏦 Komissiya: ⭐ {commission:,}"
                    f"{nft_text}",
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(
                    p["telegram_id"],
                    f"😔 <b>Mag'lubiyat</b>\n\n"
                    f"🎮 O'yin: <code>#{room_id[-6:]}</code>\n"
                    f"💸 Stavka: ⭐ {p['bet']:,}\n"
                    f"🏆 G'olib: {winner.get('first_name', 'Noma\\'lum')}",
                    parse_mode="HTML"
                )
    except Exception:
        pass

    # Cleanup after 30s
    await asyncio.sleep(30)
    active_rooms.pop(room_id, None)


async def _get_settings() -> dict:
    from backend.database import get_all_settings
    return await get_all_settings()
