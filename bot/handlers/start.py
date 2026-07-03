import os
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from backend.database import get_user, create_or_update_user, get_transactions

router = Router()

WEBAPP_URL = os.getenv("WEBAPP_URL", "http://localhost:8000")
ADMIN_PANEL_URL = os.getenv("ADMIN_PANEL_URL", "http://localhost:8000/admin")
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "supersecretadmintoken2024")


def get_main_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🎮 O'ynash",
        web_app=WebAppInfo(url=f"{WEBAPP_URL}/webapp/")
    )
    builder.button(
        text="💼 Balans",
        callback_data="balance"
    )
    builder.button(
        text="⭐ To'ldirish",
        callback_data="deposit_menu"
    )
    builder.button(
        text="📊 Tarix",
        callback_data="history"
    )
    if is_admin:
        builder.button(
            text="⚙️ Admin Panel",
            url=f"{ADMIN_PANEL_URL}?token={ADMIN_SECRET}"
        )
    builder.adjust(1, 2, 1, 1)
    return builder.as_markup()


@router.message(CommandStart())
async def cmd_start(message: Message):
    user = await create_or_update_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username or "",
        first_name=message.from_user.first_name or "",
        last_name=message.from_user.last_name or "",
    )
    name = message.from_user.first_name or "O'yinchi"
    is_admin = bool(user.get("is_admin"))

    text = (
        f"🎰 <b>Xush kelibsiz, {name}!</b>\n\n"
        f"🎮 <b>PVP Kazino</b> — real odamlar bilan o'ynang!\n\n"
        f"💼 Balans: <b>⭐ {user['balance']:,}</b>\n"
        f"🏆 G'alabalar: <b>{user['total_wins']}</b>\n"
        f"🎲 O'yinlar: <b>{user['total_games']}</b>\n\n"
        f"⬇️ Quyidagi tugmalardan foydalaning:"
    )

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=get_main_keyboard(is_admin)
    )


@router.message(Command("balance"))
async def cmd_balance(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Avval /start ni bosing")
        return
    builder = InlineKeyboardBuilder()
    builder.button(text="⭐ To'ldirish", callback_data="deposit_menu")
    builder.button(text="📊 Tarix", callback_data="history")
    builder.adjust(2)
    await message.answer(
        f"💼 <b>Balansingiz</b>\n\n"
        f"⭐ Stars: <b>{user['balance']:,}</b>\n\n"
        f"📈 Jami o'ynalgan: ⭐ {user['total_wagered']:,}\n"
        f"🏆 Jami yutilgan: ⭐ {user['total_won']:,}\n"
        f"🎲 O'yinlar: {user['total_games']} | G'alabalar: {user['total_wins']}",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


@router.message(Command("profile"))
async def cmd_profile(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Avval /start ni bosing")
        return
    win_rate = (user['total_wins'] / user['total_games'] * 100) if user['total_games'] > 0 else 0
    username_val = user.get('username') or 'yo’q'
    await message.answer(
        f"👤 <b>Profil</b>\n\n"
        f"🆔 ID: <code>{user['telegram_id']}</code>\n"
        f"👤 Ism: {user['first_name']} {user['last_name']}\n"
        f"📛 Username: @{username_val}\n\n"
        f"💼 Balans: ⭐ <b>{user['balance']:,}</b>\n"
        f"🎲 O'yinlar: {user['total_games']}\n"
        f"🏆 G'alabalar: {user['total_wins']}\n"
        f"📊 G'alaba %: {win_rate:.1f}%\n"
        f"📈 Jami stavka: ⭐ {user['total_wagered']:,}\n"
        f"💰 Jami yutgan: ⭐ {user['total_won']:,}\n\n"
        f"📅 Ro'yxat: {user['created_at'][:10]}",
        parse_mode="HTML"
    )


@router.message(Command("play"))
async def cmd_play(message: Message):
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🎮 O'yinga kirish",
        web_app=WebAppInfo(url=f"{WEBAPP_URL}/webapp/")
    )
    await message.answer(
        "🎰 <b>PVP Wheel</b> — O'yinga tayyormisiz?\n\n"
        "• Real odamlar bilan o'ynang\n"
        "• Stavkangizga qarab g'alaba ehtimoli\n"
        "• G'olib hammasini oladi!\n"
        "• NFT sovg'alar uchun katta stavka qo'ying! 🎁",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data == "balance")
async def cb_balance(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Avval /start ni bosing")
        return
    builder = InlineKeyboardBuilder()
    builder.button(text="⭐ To'ldirish", callback_data="deposit_menu")
    builder.button(text="📊 Tarix", callback_data="history")
    builder.button(text="◀️ Orqaga", callback_data="back_main")
    builder.adjust(2, 1)
    await callback.message.edit_text(
        f"💼 <b>Balansingiz</b>\n\n"
        f"⭐ Stars: <b>{user['balance']:,}</b>\n\n"
        f"📈 Jami o'ynalgan: ⭐ {user['total_wagered']:,}\n"
        f"🏆 Jami yutilgan: ⭐ {user['total_won']:,}\n"
        f"🎲 O'yinlar: {user['total_games']} | G'alabalar: {user['total_wins']}",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data == "history")
async def cb_history(callback: CallbackQuery):
    txs = await get_transactions(telegram_id=callback.from_user.id, limit=10)
    if not txs:
        text = "📊 <b>Tarix bo'sh</b>\n\nHali birorta tranzaksiya yo'q."
    else:
        lines = ["📊 <b>So'nggi 10 ta tranzaksiya:</b>\n"]
        for tx in txs:
            sign = "+" if tx["amount"] > 0 else ""
            emoji = "🟢" if tx["amount"] > 0 else "🔴"
            lines.append(f"{emoji} {sign}⭐{tx['amount']:,} — {tx['description'][:30]}")
        text = "\n".join(lines)
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Orqaga", callback_data="back_main")
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "back_main")
async def cb_back_main(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    is_admin = bool(user.get("is_admin")) if user else False
    name = callback.from_user.first_name or "O'yinchi"
    await callback.message.edit_text(
        f"🎰 <b>Xush kelibsiz, {name}!</b>\n\n"
        f"💼 Balans: ⭐ {user['balance']:,}\n"
        f"🏆 G'alabalar: {user['total_wins']}\n"
        f"🎲 O'yinlar: {user['total_games']}",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(is_admin)
    )
    await callback.answer()


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📖 <b>Yordam</b>\n\n"
        "🎮 <b>/start</b> — Bosh menyu\n"
        "💼 <b>/balance</b> — Balansni ko'rish\n"
        "👤 <b>/profile</b> — Profil\n"
        "🎰 <b>/play</b> — O'ynash\n"
        "📊 <b>/history</b> — Tranzaksiya tarixi\n"
        "⭐ <b>/deposit</b> — Balans to'ldirish\n\n"
        "❓ Muammo bo'lsa adminlarga murojaat qiling.",
        parse_mode="HTML"
    )

# Legacy reply keyboard button mapping
@router.message(F.text == "O'yinni boshlash")
async def text_play(message: Message):
    await cmd_play(message)

@router.message(F.text == "Hisobim")
async def text_balance(message: Message):
    await cmd_balance(message)

@router.message(F.text == "Statistika")
async def text_stats(message: Message):
    user = await get_user(message.from_user.id)
    if user and user.get("is_admin"):
        from bot.handlers.admin import cmd_admin
        await cmd_admin(message)
    else:
        await cmd_profile(message)

@router.message(F.text == "Sozlamalar")
async def text_settings(message: Message):
    user = await get_user(message.from_user.id)
    if user and user.get("is_admin"):
        from bot.handlers.admin import cmd_admin
        await cmd_admin(message)
