from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Any
from backend.database import get_user, create_or_update_user


class BanCheckMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable, event: Any, data: dict) -> Any:
        if isinstance(event, (Message, CallbackQuery)):
            tg_user = event.from_user
            if tg_user:
                user = await get_user(tg_user.id)
                if not user:
                    user = await create_or_update_user(
                        telegram_id=tg_user.id,
                        username=tg_user.username or "",
                        first_name=tg_user.first_name or "",
                        last_name=tg_user.last_name or "",
                    )
                
                if user.get("is_banned"):
                    if isinstance(event, Message):
                        await event.answer("🚫 Hisobingiz bloklangan. Admin bilan bog'laning.")
                    elif isinstance(event, CallbackQuery):
                        await event.answer("🚫 Hisobingiz bloklangan.", show_alert=True)
                    return

                status = user.get("approval_status", "pending")
                is_start_cmd = False
                if isinstance(event, Message) and event.text and event.text.startswith("/start"):
                    is_start_cmd = True
                
                if status == "pending":
                    if is_start_cmd:
                        return await handler(event, data)
                    if isinstance(event, Message):
                        await event.answer("⏳ Kirish so'rovingiz hali tasdiqlanmagan. Iltimos, admin javobini kuting.")
                    elif isinstance(event, CallbackQuery):
                        await event.answer("⏳ So'rovingiz tasdiqlanishini kuting.", show_alert=True)
                    return
                    
                elif status == "rejected":
                    if is_start_cmd:
                        return await handler(event, data)
                    if isinstance(event, Message):
                        await event.answer("❌ Afsuski, sizning kirish so'rovingiz rad etilgan.")
                    elif isinstance(event, CallbackQuery):
                        await event.answer("❌ Sizning kirish so'rovingiz rad etilgan.", show_alert=True)
                    return

        return await handler(event, data)
