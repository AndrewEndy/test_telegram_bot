import asyncio
from bot.database.db import engine
from bot.database.models import Base

async def init_db():
    """Ініціалізація бази даних: видалення та створення всіх таблиць."""
    async with engine.begin() as conn:
        print("Створення таблиць...")

        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("Таблиці створені успішно.")

if __name__ == "__main__":
    asyncio.run(init_db())
