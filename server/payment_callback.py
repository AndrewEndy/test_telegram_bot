# payment_callback.py
import base64
import hashlib
import json
from fastapi import FastAPI, Request, HTTPException
from bot.config import LIQPAY_PRIVATE_KEY
from bot.database.db import AsyncSessionLocal
from bot.database.models import Order
from bot.create_bot import bot

app = FastAPI()

@app.post("/payment-callback")
async def payment_callback(request: Request):
    """Обробляє callback від LiqPay після оплати."""
    try:
        # Отримуємо дані форми від LiqPay
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
        order_id = int(decoded_data["order_id"].split("_")[1])  # Витягуємо ID замовлення
        status = decoded_data["status"]

        # Оновлюємо статус замовлення в базі даних
        async with AsyncSessionLocal() as session:
            order = await session.get(Order, order_id)
            if not order:
                raise HTTPException(status_code=404, detail="Order not found")

            # Встановлюємо статус залежно від відповіді LiqPay
            if status in ("success", "sandbox"):
                order.status = "paid"
            elif status in ("failure", "error", "limit", "9859"):
                order.status = "failed"
            else:
                order.status = status
            await session.commit()

            # Якщо оплата успішна, надсилаємо деталі користувачу
            if order.status == "paid":
                # Формуємо текст із деталями замовлення
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

                # Видаляємо повідомлення з кнопкою оплати, якщо є message_id
                if order.message_id:
                    await bot.delete_message(chat_id=order.user_id, message_id=order.message_id)
                # Надсилаємо користувачу сповіщення
                await bot.send_message(order.user_id, message_text)

        return {"status": "ok"}

    except Exception as e:
        print(f"Error in payment_callback: {str(e)}")
        raise  # Кидаємо виняток, щоб FastAPI повернув 500 і ми могли відстежити проблему