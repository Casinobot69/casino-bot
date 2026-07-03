import os
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from backend.database import (
    get_user, get_stats, get_all_settings, set_setting,
    update_balance, get_all_users
)
import aiosqlite

router = Router()
DB_PATH = os.getenv("DB_PATH", "casino.db")

# Helper to check if user is admin
async def is_admin_check(telegram_id: int) -> bool:
    user = await get_user(telegram_id)
    return bool(user and user.get("is_admin"))


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not await is_admin_check(message.from_user.id):
        await message.answer("❌ Ruxsat yo'q! Siz administrator emassiz.")
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Statistika", callback_data="bot_admin_stats")
    builder.button(text="⚙️ Sozlamalar", callback_data="bot_admin_settings")
    builder.button(text="📢 Xabar (Broadcast)", callback_data="bot_admin_broadcast")
    builder.button(text="🔧 Amallar yordami", callback_data="bot_admin_help")
    builder.adjust(2)

    await message.answer(
        "👑 <b>Admin Panel (Bot versiyasi)</b>\n\n"
        "Quyidagi boshqaruv elementlaridan foydalaning yoki buyruqlar yordamini o'qing:",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data == "bot_admin_stats")
async def cb_admin_stats(callback: CallbackQuery):
    if not await is_admin_check(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    stats = await get_stats()
    text = (
        "📊 <b>Tizim Statistikasi:</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{stats['total_users']:,} ta</b>\n"
        f"📈 Bugun qo'shilgan: <b>{stats['today_users']} ta</b>\n\n"
        f"🎮 Tugallangan o'yinlar: <b>{stats['total_games']:,} ta</b>\n"
        f"⭐ Jami aylanma (Bank): <b>⭐ {stats['total_bank']:,} Stars</b>\n"
        f"🏦 Tizim komissiyasi: <b>⭐ {stats['total_commission']:,} Stars</b>\n\n"
        f"🚫 Bloklanganlar: <b>{stats['banned_users']} ta</b>\n"
        f"🎡 Hozir faol o'yinlar: <b>{stats['active_games']} ta</b>"
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Yangilash", callback_data="bot_admin_stats")
    builder.button(text="◀️ Orqaga", callback_data="bot_admin_menu")
    builder.adjust(1)
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "bot_admin_settings")
async def cb_admin_settings(callback: CallbackQuery):
    if not await is_admin_check(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    settings = await get_all_settings()
    text = (
        "⚙️ <b>O'yin Sozlamalari:</b>\n\n"
        f"• Komissiya foizi: <b>{settings.get('commission_rate', 5)}%</b>\n"
        f"• Minimal stavka: <b>⭐ {settings.get('min_bet', 100)} Stars</b>\n"
        f"• Maksimal stavka: <b>⭐ {settings.get('max_bet', 2500)} Stars</b>\n"
        f"• O'yin taymeri: <b>{settings.get('game_timer', 30)} soniya</b>\n"
        f"• Maksimal o'yinchilar: <b>{settings.get('max_players', 8)} ta</b>\n"
        f"• NFT chegarasi (Threshold): <b>⭐ {settings.get('nft_threshold', 375)} Stars</b>\n"
        f"• Yangi a'zo bonusi: <b>⭐ {settings.get('welcome_bonus', 0)} Stars</b>\n"
        f"• Texnik ishlar (Maintenance): <b>{'HA' if settings.get('maintenance_mode') == '1' else 'YO\'Q'}</b>\n\n"
        "💡 <i>Qiymatlarni o'zgartirish uchun quyidagi buyruqlardan foydalaning:</i>\n"
        "<code>/set commission_rate 5</code>\n"
        "<code>/set min_bet 100</code>\n"
        "<code>/set max_bet 2500</code>\n"
        "<code>/set maintenance_mode 1</code> (1 - yoqish, 0 - o'chirish)"
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Orqaga", callback_data="bot_admin_menu")
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "bot_admin_broadcast")
async def cb_admin_broadcast(callback: CallbackQuery):
    if not await is_admin_check(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    text = (
        "📢 <b>Hammaga xabar yuborish:</b>\n\n"
        "Barcha faol foydalanuvchilarga xabar yuborish uchun quyidagi buyruq formatidan foydalaning:\n\n"
        "<code>/sendall Xabar matni bu yerga yoziladi</code>\n\n"
        "💡 <i>HTML teglardan foydalanishingiz mumkin (<b>qalin</b>, <i>og'ma</i>, va h.k.).</i>"
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Orqaga", callback_data="bot_admin_menu")
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "bot_admin_help")
async def cb_admin_help(callback: CallbackQuery):
    if not await is_admin_check(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    text = (
        "🔧 <b>Tezkor Buyruqlar Yordamnomasi:</b>\n\n"
        "👤 <b>Foydalanuvchini ban qilish:</b>\n"
        "<code>/ban ID_RAQAMI Sababi</code>\n"
        "Misol: <code>/ban 12345678 qoidabuzar</code>\n\n"
        "✅ <b>Blokdan chiqarish:</b>\n"
        "<code>/unban ID_RAQAMI</code>\n\n"
        "💰 <b>Balans to'ldirish (ID orqali):</b>\n"
        "<code>/plus ID_RAQAMI MIQDOR</code>\n"
        "Misol: <code>/plus 12345678 500</code>\n\n"
        "💸 <b>Balansdan ayirish (ID orqali):</b>\n"
        "<code>/minus ID_RAQAMI MIQDOR</code>\n\n"
        "👑 <b>Admin berish:</b>\n"
        "<code>/makeadmin ID_RAQAMI</code>\n\n"
        "❌ <b>Admin huquqini olish:</b>\n"
        "<code>/removeadmin ID_RAQAMI</code>"
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Orqaga", callback_data="bot_admin_menu")
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "bot_admin_menu")
async def cb_admin_menu(callback: CallbackQuery):
    if not await is_admin_check(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Statistika", callback_data="bot_admin_stats")
    builder.button(text="⚙️ Sozlamalar", callback_data="bot_admin_settings")
    builder.button(text="📢 Xabar (Broadcast)", callback_data="bot_admin_broadcast")
    builder.button(text="🔧 Amallar yordami", callback_data="bot_admin_help")
    builder.adjust(2)

    await callback.message.edit_text(
        "👑 <b>Admin Panel (Bot versiyasi)</b>\n\n"
        "Quyidagi boshqaruv elementlaridan foydalaning yoki buyruqlar yordamini o'qing:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


# ─── CMD HANDLERS ─────────────────────────────────────────

@router.message(Command("plus"))
async def admin_cmd_plus(message: Message):
    if not await is_admin_check(message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 3:
        await message.answer("⚠️ Format: <code>/plus telegram_id miqdor</code>")
        return
    try:
        tg_id = int(args[1])
        amount = int(args[2])
        if amount <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Noto'g'ri ID yoki miqdor")
        return

    try:
        updated = await update_balance(tg_id, amount, "admin_add", f"Admin bot orqali qo'shdi: +{amount}")
        await message.answer(f"✅ Foydalanuvchi #{tg_id} balansiga <b>⭐ {amount:,} Stars</b> qo'shildi!\nYangi balans: ⭐ {updated['balance']:,}")
        
        # Notify user
        try:
            from bot.main import bot
            await bot.send_message(
                tg_id,
                f"💰 <b>Balansingiz to'ldirildi!</b>\n\n"
                f"➕ Qo'shildi: ⭐ {amount:,}\n"
                f"💼 Joriy balans: ⭐ {updated['balance']:,}"
            )
        except Exception:
            pass
    except Exception as e:
        await message.answer(f"❌ Xato: {str(e)}")


@router.message(Command("minus"))
async def admin_cmd_minus(message: Message):
    if not await is_admin_check(message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 3:
        await message.answer("⚠️ Format: <code>/minus telegram_id miqdor</code>")
        return
    try:
        tg_id = int(args[1])
        amount = int(args[2])
        if amount <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Noto'g'ri ID yoki miqdor")
        return

    try:
        user = await get_user(tg_id)
        if not user:
            await message.answer("❌ Foydalanuvchi topilmadi")
            return
        if user["balance"] < amount:
            await message.answer("❌ Balans yetarli emas")
            return
        updated = await update_balance(tg_id, -amount, "admin_remove", f"Admin bot orqali ayirdi: -{amount}")
        await message.answer(f"✅ Foydalanuvchi #{tg_id} balansidan <b>⭐ {amount:,} Stars</b> ayirildi!\nYangi balans: ⭐ {updated['balance']:,}")
        
        # Notify user
        try:
            from bot.main import bot
            await bot.send_message(
                tg_id,
                f"💸 <b>Balansingizdan ayirildi</b>\n\n"
                f"➖ Ayirildi: ⭐ {amount:,}\n"
                f"💼 Joriy balans: ⭐ {updated['balance']:,}"
            )
        except Exception:
            pass
    except Exception as e:
        await message.answer(f"❌ Xato: {str(e)}")


@router.message(Command("ban"))
async def admin_cmd_ban(message: Message):
    if not await is_admin_check(message.from_user.id):
        return
    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        await message.answer("⚠️ Format: <code>/ban telegram_id sabab</code>")
        return
    try:
        tg_id = int(args[1])
        reason = args[2] if len(args) > 2 else "Ko'rsatilmagan"
    except ValueError:
        await message.answer("❌ Noto'g'ri ID")
        return

    user = await get_user(tg_id)
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi")
        return

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned=1 WHERE telegram_id=?", (tg_id,))
        await db.commit()

    await message.answer(f"🚫 Foydalanuvchi #{tg_id} bloklandi!")

    try:
        from bot.main import bot
        await bot.send_message(
            tg_id,
            f"🚫 <b>Hisobingiz bloklandi</b>\n\n"
            f"Sabab: {reason}\n\n"
            f"Murojaat uchun: admin bilan bog'laning"
        )
    except Exception:
        pass


@router.message(Command("unban"))
async def admin_cmd_unban(message: Message):
    if not await is_admin_check(message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("⚠️ Format: <code>/unban telegram_id</code>")
        return
    try:
        tg_id = int(args[1])
    except ValueError:
        await message.answer("❌ Noto'g'ri ID")
        return

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned=0 WHERE telegram_id=?", (tg_id,))
        await db.commit()

    await message.answer(f"✅ Foydalanuvchi #{tg_id} blokdan chiqarildi!")

    try:
        from bot.main import bot
        await bot.send_message(
            tg_id,
            "✅ <b>Hisobingiz tiklandi!</b>\n\nEndi botdan foydalanishingiz mumkin."
        )
    except Exception:
        pass


@router.message(Command("set"))
async def admin_cmd_set(message: Message):
    if not await is_admin_check(message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 3:
        await message.answer("⚠️ Format: <code>/set kalit qiymat</code>\nMasalan: <code>/set commission_rate 8</code>")
        return
    key = args[1]
    value = args[2]

    valid_keys = ['commission_rate', 'min_bet', 'max_bet', 'game_timer', 'max_players', 'nft_threshold', 'welcome_bonus', 'maintenance_mode']
    if key not in valid_keys:
        await message.answer(f"❌ Noto'g'ri sozlama kaliti. Faqat shular: {', '.join(valid_keys)}")
        return

    await set_setting(key, value)
    await message.answer(f"✅ Sozlama o'zgartirildi:\n<b>{key}</b> ➔ <code>{value}</code>")


@router.message(Command("sendall"))
async def admin_cmd_sendall(message: Message):
    if not await is_admin_check(message.from_user.id):
        return
    broadcast_text = message.text[len("/sendall "):].strip()
    if not broadcast_text:
        await message.answer("⚠️ Xabar matnini kiriting: <code>/sendall matn</code>")
        return

    status_msg = await message.answer("⏳ Xabar yuborilmoqda...")
    users = await get_all_users(limit=10000)
    sent = 0
    failed = 0

    from bot.main import bot
    for u in users:
        if u.get("is_banned"):
            continue
        try:
            await bot.send_message(
                u["telegram_id"],
                f"📢 <b>Xabar</b>\n\n{broadcast_text}",
                parse_mode="HTML"
            )
            sent += 1
        except Exception:
            failed += 1

    # Log to DB
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO messages (from_admin, message, sent_count) VALUES (1, ?, ?)", (broadcast_text, sent))
        await db.commit()

    await status_msg.edit_text(f"✅ Yuborildi: {sent} ta | Xato: {failed} ta")


@router.message(Command("makeadmin"))
async def admin_cmd_makeadmin(message: Message):
    if not await is_admin_check(message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("⚠️ Format: <code>/makeadmin telegram_id</code>")
        return
    try:
        tg_id = int(args[1])
    except ValueError:
        await message.answer("❌ Noto'g'ri ID")
        return

    user = await get_user(tg_id)
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi")
        return

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_admin=1 WHERE telegram_id=?", (tg_id,))
        await db.commit()

    await message.answer(f"👑 Foydalanuvchi #{tg_id} admin qilindi!")
    try:
        from bot.main import bot
        await bot.send_message(tg_id, "👑 Sizga <b>Admin</b> huquqi berildi!", parse_mode="HTML")
    except Exception:
        pass


@router.message(Command("removeadmin"))
async def admin_cmd_removeadmin(message: Message):
    if not await is_admin_check(message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("⚠️ Format: <code>/removeadmin telegram_id</code>")
        return
    try:
        tg_id = int(args[1])
    except ValueError:
        await message.answer("❌ Noto'g'ri ID")
        return

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_admin=0 WHERE telegram_id=?", (tg_id,))
        await db.commit()

    await message.answer(f"✅ Foydalanuvchi #{tg_id} dan admin huquqi olindi!")
