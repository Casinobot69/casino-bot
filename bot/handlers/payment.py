from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from backend.database import get_user, update_balance

router = Router()

DEPOSIT_OPTIONS = [
    (50,   "⭐ 50 Stars",   "Boshlang'ich"),
    (100,  "⭐ 100 Stars",  "Standart"),
    (250,  "⭐ 250 Stars",  "O'rta"),
    (500,  "⭐ 500 Stars",  "Premium"),
    (1000, "⭐ 1000 Stars", "Pro"),
    (2500, "⭐ 2500 Stars", "VIP"),
    (5000, "⭐ 5000 Stars", "Mega VIP"),
]


@router.message(Command("deposit"))
@router.callback_query(F.data == "deposit_menu")
async def deposit_menu(event: Message | CallbackQuery):
    builder = InlineKeyboardBuilder()
    for amount, label, tier in DEPOSIT_OPTIONS:
        builder.button(text=f"{label} ({tier})", callback_data=f"deposit_{amount}")
    builder.button(text="◀️ Orqaga", callback_data="back_main")
    builder.adjust(1)
    text = (
        "⭐ <b>Balans To'ldirish</b>\n\n"
        "Miqdorni tanlang:\n\n"
        "💡 <i>To'lov Telegram Stars orqali amalga oshiriladi</i>"
    )
    if isinstance(event, Message):
        await event.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())
    else:
        await event.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())
        await event.answer()


@router.callback_query(F.data.startswith("deposit_"))
async def deposit_amount(callback: CallbackQuery):
    try:
        amount = int(callback.data.split("_")[1])
    except Exception:
        await callback.answer("❌ Xato")
        return

    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Avval /start bosing")
        return

    # Send Stars invoice
    from bot.main import bot
    try:
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title=f"⭐ {amount} Stars",
            description=f"Kazino balansingizga {amount} Stars qo'shiladi",
            payload=f"deposit_{amount}_{callback.from_user.id}",
            currency="XTR",
            prices=[LabeledPrice(label=f"{amount} Stars", amount=amount)],
        )
        await callback.answer("✅ To'lov so'rovi yuborildi!")
    except Exception as e:
        await callback.answer(f"❌ Xato: {str(e)[:100]}", show_alert=True)


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    amount = message.successful_payment.total_amount  # In Stars, amount = stars

    user = await get_user(message.from_user.id)
    if not user:
        return

    updated = await update_balance(
        telegram_id=message.from_user.id,
        amount=amount,
        tx_type="deposit",
        description=f"Telegram Stars to'lovi: +{amount}"
    )

    await message.answer(
        f"✅ <b>To'lov muvaffaqiyatli!</b>\n\n"
        f"⭐ Qo'shildi: <b>{amount:,} Stars</b>\n"
        f"💼 Joriy balans: <b>⭐ {updated['balance']:,}</b>\n\n"
        f"🎮 Endi o'ynashingiz mumkin!",
        parse_mode="HTML"
    )
