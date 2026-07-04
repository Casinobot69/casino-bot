import aiosqlite
import os
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", "casino.db")

NFT_PRIZES = [
    {"id": 1,  "name": "Siamese Cat",    "emoji": "🐱", "image": "🐱", "price": 20249},
    {"id": 2,  "name": "Gym",            "emoji": "💪", "image": "💪", "price": 12958},
    {"id": 3,  "name": "Handbag",        "emoji": "👜", "image": "👜", "price": 12514},
    {"id": 4,  "name": "Storage Box",    "emoji": "📦", "image": "📦", "price": 6632},
    {"id": 5,  "name": "Diamond Ring",   "emoji": "💍", "image": "💍", "price": 3262},
    {"id": 6,  "name": "Hair Dryer",     "emoji": "💨", "image": "💨", "price": 1597},
    {"id": 7,  "name": "Pumpkin",        "emoji": "🎃", "image": "🎃", "price": 1144},
    {"id": 8,  "name": "White Flower",   "emoji": "🌸", "image": "🌸", "price": 940},
    {"id": 9,  "name": "Monkey Painter", "emoji": "🐒", "image": "🐒", "price": 820},
    {"id": 10, "name": "Magic Wand",     "emoji": "✨", "image": "✨", "price": 723},
    {"id": 11, "name": "Angel Gift",     "emoji": "👼", "image": "👼", "price": 684},
    {"id": 12, "name": "Bunny",          "emoji": "🐰", "image": "🐰", "price": 420},
    {"id": 13, "name": "Banana",         "emoji": "🍌", "image": "🍌", "price": 405},
    {"id": 14, "name": "Galaxy Lens",    "emoji": "🔮", "image": "🔮", "price": 398},
    {"id": 15, "name": "Hobbit House",   "emoji": "🏡", "image": "🏡", "price": 397},
    {"id": 16, "name": "Swirl",          "emoji": "🌀", "image": "🌀", "price": 392},
    {"id": 17, "name": "2025",           "emoji": "🎊", "image": "🎊", "price": 378},
    {"id": 18, "name": "Ice Cream",      "emoji": "🍦", "image": "🍦", "price": 376},
    {"id": 19, "name": "Ghost Box",      "emoji": "👻", "image": "👻", "price": 375},
    {"id": 20, "name": "Torch",          "emoji": "🕯️", "image": "🕯️", "price": 375},
    {"id": 21, "name": "Stars Bonus",    "emoji": "⭐", "image": "⭐", "price": 100},
]


def _dict_factory(cursor, row):
    fields = [description[0] for description in cursor.description]
    return {k: v for k, v in zip(fields, row)}


async def _fetchone(db, query, params=()):
    async with db.execute(query, params) as cursor:
        row = await cursor.fetchone()
        if row is None:
            return None
        return _dict_factory(cursor, row)


async def _fetchall(db, query, params=()):
    async with db.execute(query, params) as cursor:
        rows = await cursor.fetchall()
        return [_dict_factory(cursor, row) for row in rows]


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT DEFAULT '',
                first_name TEXT DEFAULT '',
                last_name TEXT DEFAULT '',
                photo_url TEXT DEFAULT '',
                balance INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                total_games INTEGER DEFAULT 0,
                total_wins INTEGER DEFAULT 0,
                total_wagered INTEGER DEFAULT 0,
                total_won INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_seen TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'waiting',
                total_bank INTEGER DEFAULT 0,
                commission INTEGER DEFAULT 0,
                winner_id INTEGER DEFAULT NULL,
                winner_telegram_id INTEGER DEFAULT NULL,
                winner_amount INTEGER DEFAULT 0,
                nft_prize TEXT DEFAULT NULL,
                game_hash TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                finished_at TEXT DEFAULT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS game_players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                telegram_id INTEGER NOT NULL,
                username TEXT DEFAULT '',
                first_name TEXT DEFAULT '',
                bet_amount INTEGER NOT NULL,
                chance REAL DEFAULT 0,
                is_winner INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                telegram_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                amount INTEGER NOT NULL,
                description TEXT DEFAULT '',
                balance_before INTEGER DEFAULT 0,
                balance_after INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_admin INTEGER NOT NULL,
                message TEXT NOT NULL,
                sent_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                telegram_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                details TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                processed_at TEXT DEFAULT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS promo_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                reward INTEGER NOT NULL,
                max_uses INTEGER DEFAULT 1,
                uses INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_promos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                promo_id INTEGER NOT NULL,
                used_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                details TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        defaults = [
            ("commission_rate", "5"),
            ("min_bet", "100"),
            ("max_bet", "2500"),
            ("game_timer", "30"),
            ("max_players", "8"),
            ("nft_threshold", "375"),
            ("maintenance_mode", "0"),
            ("welcome_bonus", "0"),
            ("referral_bonus", "0"),
        ]
        for key, value in defaults:
            await db.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value)
            )
        await db.commit()
    print(f"✅ Database initialized: {DB_PATH}")


async def get_setting(key: str, default: str = None) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else default


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )
        await db.commit()


async def get_all_settings() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        rows = await _fetchall(db, "SELECT key, value FROM settings")
        return {r["key"]: r["value"] for r in rows}


async def get_user(telegram_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        return await _fetchone(db, "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))


async def get_user_by_id(user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        return await _fetchone(db, "SELECT * FROM users WHERE id = ?", (user_id,))


async def create_or_update_user(telegram_id: int, username: str = "", first_name: str = "",
                                 last_name: str = "", photo_url: str = "") -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        existing = await _fetchone(db, "SELECT * FROM users WHERE telegram_id=?", (telegram_id,))
        welcome_bonus = int(await get_setting("welcome_bonus") or "0")
        if not existing:
            await db.execute(
                "INSERT INTO users (telegram_id, username, first_name, last_name, photo_url, balance) VALUES (?,?,?,?,?,?)",
                (telegram_id, username, first_name, last_name, photo_url, welcome_bonus)
            )
        else:
            await db.execute(
                "UPDATE users SET username=?, first_name=?, last_name=?, photo_url=?, last_seen=CURRENT_TIMESTAMP WHERE telegram_id=?",
                (username, first_name, last_name, photo_url, telegram_id)
            )
        await db.commit()
    return await get_user(telegram_id)


async def update_balance(telegram_id: int, amount: int, tx_type: str, description: str = "") -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        user = await _fetchone(db, "SELECT * FROM users WHERE telegram_id=?", (telegram_id,))
        if not user:
            raise ValueError("User not found")
        balance_before = user["balance"]
        balance_after = balance_before + amount
        if balance_after < 0:
            raise ValueError("Insufficient balance")
        await db.execute("UPDATE users SET balance=balance+? WHERE telegram_id=?", (amount, telegram_id))
        await db.execute(
            "INSERT INTO transactions (user_id, telegram_id, type, amount, description, balance_before, balance_after) VALUES (?,?,?,?,?,?,?)",
            (user["id"], telegram_id, tx_type, amount, description, balance_before, balance_after)
        )
        await db.commit()
    return await get_user(telegram_id)


async def get_all_users(limit: int = 100, offset: int = 0, search: str = "") -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        if search:
            s = f"%{search}%"
            return await _fetchall(db,
                "SELECT * FROM users WHERE username LIKE ? OR first_name LIKE ? OR CAST(telegram_id AS TEXT) LIKE ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (s, s, s, limit, offset))
        return await _fetchall(db, "SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset))


async def get_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        def q(query):
            return _fetchone(db, query)

        total_users = (await q("SELECT COUNT(*) as c FROM users"))["c"]
        total_games = (await q("SELECT COUNT(*) as c FROM games WHERE status='finished'"))["c"]
        total_bank = (await q("SELECT COALESCE(SUM(total_bank),0) as s FROM games WHERE status='finished'"))["s"]
        total_commission = (await q("SELECT COALESCE(SUM(commission),0) as s FROM games WHERE status='finished'"))["s"]
        active_games = (await q("SELECT COUNT(*) as c FROM games WHERE status IN ('waiting','playing','betting','spinning')"))["c"]
        banned_users = (await q("SELECT COUNT(*) as c FROM users WHERE is_banned=1"))["c"]
        today_users = (await q("SELECT COUNT(*) as c FROM users WHERE DATE(created_at)=DATE('now')"))["c"]
        today_games = (await q("SELECT COUNT(*) as c FROM games WHERE status='finished' AND DATE(created_at)=DATE('now')"))["c"]
        return {
            "total_users": total_users, "total_games": total_games,
            "total_bank": total_bank, "total_commission": total_commission,
            "active_games": active_games, "banned_users": banned_users,
            "today_users": today_users, "today_games": today_games,
        }


async def get_transactions(telegram_id: int = None, limit: int = 20) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        if telegram_id:
            return await _fetchall(db, "SELECT * FROM transactions WHERE telegram_id=? ORDER BY created_at DESC LIMIT ?", (telegram_id, limit))
        return await _fetchall(db, "SELECT * FROM transactions ORDER BY created_at DESC LIMIT ?", (limit,))


async def get_game_history(limit: int = 20) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        return await _fetchall(db, "SELECT * FROM games WHERE status='finished' ORDER BY finished_at DESC LIMIT ?", (limit,))


async def add_audit_log(action: str, details: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO audit_logs (action, details) VALUES (?, ?)", (action, details))
        await db.commit()


async def get_audit_logs(limit: int = 50) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        return await _fetchall(db, "SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT ?", (limit,))


async def create_promo(code: str, reward: int, max_uses: int = 1) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("INSERT INTO promo_codes (code, reward, max_uses) VALUES (?, ?, ?)", (code, reward, max_uses))
            await db.commit()
            return True
        except Exception:
            return False


async def get_promos() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        return await _fetchall(db, "SELECT * FROM promo_codes ORDER BY created_at DESC")


async def delete_promo(promo_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM promo_codes WHERE id=?", (promo_id,))
        await db.commit()


async def claim_promo(telegram_id: int, code: str) -> tuple[bool, str]:
    async with aiosqlite.connect(DB_PATH) as db:
        user = await _fetchone(db, "SELECT * FROM users WHERE telegram_id=?", (telegram_id,))
        if not user:
            return False, "Foydalanuvchi topilmadi"
        
        promo = await _fetchone(db, "SELECT * FROM promo_codes WHERE code=?", (code,))
        if not promo:
            return False, "Promo-kod topilmadi"
        
        if promo["uses"] >= promo["max_uses"]:
            return False, "Promo-koddan foydalanish soni tugagan"
            
        already_used = await _fetchone(db, "SELECT * FROM user_promos WHERE user_id=? AND promo_id=?", (user["id"], promo["id"]))
        if already_used:
            return False, "Siz ushbu promo-koddan allaqachon foydalangansiz"
            
        await db.execute("UPDATE users SET balance=balance+? WHERE id=?", (promo["reward"], user["id"]))
        await db.execute("INSERT INTO user_promos (user_id, promo_id) VALUES (?, ?)", (user["id"], promo["id"]))
        await db.execute("UPDATE promo_codes SET uses=uses+1 WHERE id=?", (promo["id"],))
        await db.execute(
            """INSERT INTO transactions (user_id, telegram_id, type, amount, description, balance_before, balance_after)
               VALUES (?, ?, 'promo_redeem', ?, ?, ?, ?)""",
            (user["id"], telegram_id, promo["reward"], f"Promo-kod: {code}", user["balance"], user["balance"] + promo["reward"])
        )
        await db.commit()
        return True, f"Tabriklaymiz! Hisobingizga ⭐ {promo['reward']} Stars qo'shildi."


async def create_withdrawal(telegram_id: int, amount: int, details: str = "") -> tuple[bool, str]:
    async with aiosqlite.connect(DB_PATH) as db:
        user = await _fetchone(db, "SELECT * FROM users WHERE telegram_id=?", (telegram_id,))
        if not user:
            return False, "Foydalanuvchi topilmadi"
        if user["balance"] < amount:
            return False, "Balansingiz yetarli emas"
            
        await db.execute("UPDATE users SET balance=balance-? WHERE id=?", (amount, user["id"]))
        await db.execute(
            "INSERT INTO withdrawals (user_id, telegram_id, amount, status, details) VALUES (?, ?, ?, 'pending', ?)",
            (user["id"], telegram_id, amount, details)
        )
        await db.execute(
            """INSERT INTO transactions (user_id, telegram_id, type, amount, description, balance_before, balance_after)
               VALUES (?, ?, 'withdrawal_pending', ?, ?, ?, ?)""",
            (user["id"], telegram_id, -amount, f"Chiqazish so'rovi: {details}", user["balance"], user["balance"] - amount)
        )
        await db.commit()
        return True, "Chiqazish so'rovi qabul qilindi. Admin tasdiqlashini kuting."


async def get_withdrawals(status: str = None) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        if status:
            return await _fetchall(db, "SELECT * FROM withdrawals WHERE status=? ORDER BY created_at DESC", (status,))
        return await _fetchall(db, "SELECT * FROM withdrawals ORDER BY created_at DESC")


async def process_withdrawal(withdrawal_id: int, action: str) -> tuple[bool, str]:
    async with aiosqlite.connect(DB_PATH) as db:
        w = await _fetchone(db, "SELECT * FROM withdrawals WHERE id=?", (withdrawal_id,))
        if not w:
            return False, "So'rov topilmadi"
        if w["status"] != "pending":
            return False, "Ushbu so'rov allaqachon bajarilgan"
            
        if action == "approve":
            await db.execute("UPDATE withdrawals SET status='approved', processed_at=CURRENT_TIMESTAMP WHERE id=?", (withdrawal_id,))
            await db.execute(
                "UPDATE transactions SET type='withdrawal_approved' WHERE telegram_id=? AND amount=? AND type='withdrawal_pending'",
                (w["telegram_id"], -w["amount"])
            )
            await db.commit()
            return True, "Tasdiqlandi!"
        else:
            await db.execute("UPDATE users SET balance=balance+? WHERE telegram_id=?", (w["amount"], w["telegram_id"]))
            await db.execute("UPDATE withdrawals SET status='rejected', processed_at=CURRENT_TIMESTAMP WHERE id=?", (withdrawal_id,))
            
            user = await _fetchone(db, "SELECT id, balance FROM users WHERE telegram_id=?", (w["telegram_id"],))
            await db.execute(
                """INSERT INTO transactions (user_id, telegram_id, type, amount, description, balance_before, balance_after)
                   VALUES (?, ?, 'withdrawal_refund', ?, ?, ?, ?)""",
                (user["id"], w["telegram_id"], w["amount"], f"Chiqazish rad etildi (qaytarildi)", user["balance"] - w["amount"], user["balance"])
            )
            await db.commit()
            return True, "Rad etildi (Mablag' qaytarildi)"
