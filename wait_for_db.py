import asyncio
import sys

try:
    from src.db.engine import engine
except ImportError:
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from src.db.engine import engine


async def wait():
    for i in range(30):
        try:
            async with engine.connect() as conn:
                await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
            print("[wait] postgres is ready")
            return
        except Exception as e:
            print(f"[wait] attempt {i + 1}/30 failed: {e}")
            await asyncio.sleep(1)
    print("[wait] could not connect to postgres")
    sys.exit(1)


if __name__ == "__main__":
    asyncio.run(wait())
