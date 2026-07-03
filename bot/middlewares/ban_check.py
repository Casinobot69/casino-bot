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
                if user and user.get("is_banned"):
                    if isinstance(event, Message):
                        await event.answer("🚫 Hisobingiz bloklangan. Admin bilan bog'laning.")
                    elif isinstance(event, CallbackQuery):
                        await event.answer("🚫 Hisobingiz bloklangan.", show_alert=True)
                    return
                # Auto-register
                if not user:
                    await create_or_update_user(
                        telegram_id=tg_user.id,
                        username=tg_user.username or "",
                        first_name=tg_user.first_name or "",
                        last_name=tg_user.last_name or "",
                    )
        return await handler(event, data)
