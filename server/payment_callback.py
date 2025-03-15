# server/payment_callback.py
import base64
import hashlib
import json
from fastapi import FastAPI, Request, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import joinedload
from bot.config import LIQPAY_PRIVATE_KEY
from bot.database.db import AsyncSessionLocal
from bot.database.models import Order, Cart
from bot.create_bot import bot

app = FastAPI()

@app.post("/payment-callback")
async def payment_callback(request: Request):
    """Обробляє callback від LiqPay після оплати."""
    try:
        # Отримуємо дані від LiqPay
        form_data = await request.form()
        data = form_data.get("data")
        signature = form_data.get("signature")

        # Перевіряємо наявність даних і підпису
        if not data or not signature:
            raise HTTPException(status_code=400, detail="Missing data or signature")

        # Перевіряємо валідність підпису
        sign_str = LIQPAY_PRIVATE_KEY + data + LIQPAY_PRIVATE_KEY
        expected_signature = base64.b64encode(hashlib.sha1(sign_str.encode()).digest()).decode()
        if signature != expected_signature:
            raise HTTPException(status_code=403, detail="Invalid signature")

        # Декодуємо дані від LiqPay
        decoded_data = json.loads(base64.b64decode(data).decode())
        order_id = decoded_data["order_id"]  # Формат: "cart_userid_timestamp"
        status = decoded_data["status"]
        print(f"Full LiqPay response: {decoded_data}")

        async with AsyncSessionLocal() as session:
            # Витягуємо user_id із order_id
            user_id = int(order_id.split("_")[1])

            # Отримуємо кошик із пов’язаними продуктами
            cart_items = (await session.execute(
                select(Cart).options(joinedload(Cart.product)).where(Cart.user_id == user_id)
            )).scalars().all()

            if not cart_items:
                raise HTTPException(status_code=404, detail="Cart is empty")

            # Обчислюємо загальну суму і формуємо список товарів
            total_price = float(sum(item.product.price * item.quantity for item in cart_items))
            items = [
                {
                    "name": item.product.name,
                    "variant": item.variant,
                    "quantity": item.quantity,
                    "price_per_unit": float(item.product.price),
                    "total": float(item.product.price * item.quantity)
                }
                for item in cart_items
            ]

            # Отримуємо message_id із першого елемента кошика (він однаковий для всіх)
            message_id = cart_items[0].message_id if cart_items else None

            # Обробляємо успішну оплату
            if status in ("success", "sandbox"):
                # Створюємо замовлення
                order = Order(
                    user_id=user_id,
                    total_price=total_price,
                    items=items,
                    status="paid"
                )
                session.add(order)
                await session.commit()

                # Очищаємо кошик
                await session.execute(delete(Cart).where(Cart.user_id == user_id))
                await session.commit()

                # Формуємо текст сповіщення
                items_text = "\n".join(
                    f"- {item['name']} ({item['variant']}) - {item['quantity']} шт. за {item['total']} грн"
                    for item in order.items
                )
                message_text = (
                    f"✅ Оплата пройшла успішно, дякуємо за покупку!\n\n"
                    f"<b>Деталі замовлення:</b>\n"
                    f"{items_text}\n\n"
                    f"<b>Загальна сума:</b> {order.total_price} грн\n"
                    f"<b>Дата:</b> {order.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
                )

                # Видаляємо повідомлення кошика, якщо є message_id
                if message_id:
                    await bot.delete_message(chat_id=user_id, message_id=message_id)
                # Надсилаємо сповіщення про успіх
                await bot.send_message(user_id, message_text)

            # Обробляємо неуспішну оплату
            elif status in ("failure", "error"):
                # Видаляємо повідомлення кошика, якщо є message_id
                if message_id:
                    await bot.delete_message(chat_id=user_id, message_id=message_id)
                # Надсилаємо сповіщення про помилку
                await bot.send_message(user_id, "❌ Помилка оплати. Спробуйте ще раз.")

        return {"status": "ok"}

    except Exception as e:
        print(f"Error in payment_callback: {str(e)}")
        raise