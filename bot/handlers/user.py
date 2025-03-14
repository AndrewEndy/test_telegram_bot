from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from sqlalchemy import delete
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from bot.create_bot import bot
from bot.database.models import User, Product, Cart, Order
from bot.database.db import AsyncSessionLocal
from bot.keyboards.inline_keyboards import get_product_variants_keyboard
from bot.services.liqpay import generate_payment_link

user_router = Router()


async def get_all_products(message: types.Message, session: AsyncSessionLocal):
    result = await session.execute(select(Product))
    products = result.scalars().all()

    if not products:
        await message.answer("Наразі товарів немає в наявності.")
        return

    # Відправляємо кожен товар окремим повідомленням з кнопками
    for product in products:
        text = f"🛒 <b>{product.name}</b>\n\nОпис: {product.description}\n💰 Ціна: {product.price} грн"
        await message.answer(text, reply_markup=get_product_variants_keyboard(product))


# Обробка команди /start
@user_router.message(Command("start"))
async def start_command(message: types.Message):
    async with AsyncSessionLocal() as session:
        user = await session.get(User, message.from_user.id)

        if not user: # Якщо це новий юзер
            user = User(tg_id=message.from_user.id, username=message.from_user.username or "Unknown")
            session.add(user)
            await session.commit()

        # Створюємо reply-клавіатуру
        reply_kb = ReplyKeyboardBuilder()
        reply_kb.button(text="🛒 Корзина")
        reply_kb.button(text="📦 Асортимент")

        await message.answer(
            f"Привіт, {user.username}! 👋\n"
            "Я допоможу тобі купити товари. Ось доступні товари:",
            reply_markup=reply_kb.as_markup(resize_keyboard=True)
        )

        # Отримуємо всі товари
        await get_all_products(message, session)


# Обробка команди /products
@user_router.message(Command("products"))
async def products_command(message: types.Message):
    async with AsyncSessionLocal() as session:
        # Отримуємо всі товари
        await get_all_products(message, session)


# Обробка reply кнопки "📦 Асортимент"
@user_router.message(F.text == "📦 Асортимент")
async def products_command(message: types.Message):
    async with AsyncSessionLocal() as session:
        # Отримуємо всі товари
        await get_all_products(message, session)


# Обробник додавання товару в кошик
@user_router.callback_query(F.data.startswith("variant_"))
async def add_to_cart(callback: types.CallbackQuery):
    _, product_id, variant = callback.data.split("_")
    product_id = int(product_id)

    async with AsyncSessionLocal() as session:
        product = await session.get(Product, product_id)

        if not product:
            await callback.answer("❌ Товар не знайдено", show_alert=True)
            return

        # Перевіряємо, чи товар вже є в кошику
        existing_cart_item = await session.execute(
            select(Cart).where(Cart.user_id == callback.from_user.id, Cart.product_id == product_id,
                               Cart.variant == variant)
        )
        cart_item = existing_cart_item.scalars().first()

        if cart_item:
            cart_item.quantity += 1  # Якщо є, збільшуємо кількість
        else:
            cart_item = Cart(user_id=callback.from_user.id, product_id=product_id, variant=variant, quantity=1)
            session.add(cart_item)

        await session.commit()

    await callback.answer(f"✅ {product.name} ({variant}) додано до кошика!")


# Обробник reply кнопки "Кошик"
@user_router.message(F.text == "🛒 Корзина")
async def show_cart(message: types.Message):
    async with AsyncSessionLocal() as session:
        cart_items = await session.execute(
            select(Cart).options(joinedload(Cart.product)).where(Cart.user_id == message.from_user.id)
        )
        cart_items = cart_items.scalars().all()

    if not cart_items:
        await message.answer("🛒 Ваш кошик порожній")
        return

    total_price = 0
    cart_text = "🛒 <b>Ваш кошик:</b>\n\n"
    for item in cart_items:
        total_price += item.product.price * item.quantity
        cart_text += f"{item.product.name} ({item.variant}) - {item.quantity} шт.\n💰 {item.product.price * item.quantity} грн\n\n"

    cart_text += f"<b>Загальна сума: {total_price} грн</b>"

    # Додаємо кнопку "Оплатити"
    buy_button = InlineKeyboardBuilder()
    buy_button.button(text="💳 Оплатити", callback_data="checkout")

    await message.answer(cart_text, reply_markup=buy_button.as_markup())


# Формування оплати та зміни в бд
@user_router.callback_query(F.data == "checkout")
async def checkout(callback: types.CallbackQuery):
    async with AsyncSessionLocal() as session:
        cart_items = await session.execute(
            select(Cart).options(joinedload(Cart.product)).where(Cart.user_id == callback.from_user.id)
        )
        cart_items = cart_items.scalars().all()

        if not cart_items:
            await callback.answer("❌ Ваш кошик порожній", show_alert=True)
            return

        total_price = float(sum(item.product.price * item.quantity for item in cart_items))

        # Створюємо одне замовлення для всіх товарів
        order = Order(user_id=callback.from_user.id, status="pending")
        session.add(order)
        await session.commit()
        await session.refresh(order)  # Оновлюємо об'єкт, щоб отримати ID

        # Додаємо товари до замовлення (тимчасово один товар)
        for item in cart_items:
            order.product_id = item.product_id
            await session.commit()

        payment_url = generate_payment_link(total_price, f"order_{order.id}", "Оплата кошика")

        # Очищаємо кошик
        await session.execute(delete(Cart).where(Cart.user_id == callback.from_user.id))
        await session.commit()

        # Створюємо inline-кнопку з посиланням
        builder = InlineKeyboardBuilder()
        builder.button(text="💳 Оплатити", url=payment_url)

        # Редагуємо повідомлення з кнопкою і зберігаємо message_id
        sent_message = await callback.message.edit_text(
            "💳 Натисніть кнопку нижче, щоб оплатити ваше замовлення:",
            reply_markup=builder.as_markup()
        )

        # Зберігаємо message_id у базі даних
        order.message_id = sent_message.message_id
        await session.commit()


async def notify_user(order_id: int):
    async with AsyncSessionLocal() as session:
        order = await session.get(Order, order_id)
        if order.status == "paid":
            await bot.send_message(order.user_id, "✅ Оплата успішна! Ваше замовлення обробляється.")
        elif order.status == "failed":
            await bot.send_message(order.user_id, "❌ Помилка оплати. Спробуйте ще раз.")