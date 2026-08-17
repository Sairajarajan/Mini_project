import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import close_db, connect_db, ping_db


async def main():
    await connect_db()
    ok = await ping_db()
    print("MongoDB ping:", ok)
    await close_db()


asyncio.run(main())