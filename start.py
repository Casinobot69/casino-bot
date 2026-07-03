import asyncio
import os
import sys
import uvicorn
from dotenv import load_dotenv

load_dotenv()

async def main():
    # Import here to avoid circular imports
    from backend.main import app
    from bot.main import start_bot

    port = int(os.getenv("PORT", 8000))

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        loop="asyncio"
    )
    server = uvicorn.Server(config)

    print(f"🚀 Starting Casino Bot...")
    print(f"🌐 Server: http://0.0.0.0:{port}")
    print(f"🎮 WebApp: http://0.0.0.0:{port}/webapp/")
    print(f"⚙️  Admin: http://0.0.0.0:{port}/admin/")

    await asyncio.gather(
        server.serve(),
        start_bot()
    )

if __name__ == "__main__":
    asyncio.run(main())
