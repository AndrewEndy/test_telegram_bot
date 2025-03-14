import asyncio
from aiogram.types import BotCommand, BotCommandScopeDefault
from bot.create_bot import bot, dp
from bot.config import ADMINS

from bot.handlers.user import user_router



async def set_commands():
    commands = [BotCommand(command='start', description='Запустити/перезапустити бота'),
                BotCommand(command='products', description='Список продуктів'),
                ]
    await bot.set_my_commands(commands, BotCommandScopeDefault())


async def start_bot():
    await set_commands()

    try:
        for admin_id in ADMINS:
            await bot.send_message(admin_id, f'Бот запущений')
    except:
        pass



async def stop_bot():
    try:
        for admin_id in ADMINS:
            await bot.send_message(admin_id, 'Бот виключений')
    except:
        pass


async def main():
    dp.include_router(user_router)

    dp.startup.register(start_bot)
    dp.shutdown.register(stop_bot)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f'\033[32mБот завершив роботу\033[0m')
