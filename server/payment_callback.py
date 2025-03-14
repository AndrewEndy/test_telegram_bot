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
    form_data = await request.form()
    data = form_data.get("data")
    signature = form_data.get("signature")
    print(f"Received callback: data={data}, signature={signature}")

    if not data or not signature:
        raise HTTPException(status_code=400, detail="Missing data or signature")

    # Перевіряємо підпис
    sign_str = LIQPAY_PRIVATE_KEY + data + LIQPAY_PRIVATE_KEY
    expected_signature = base64.b64encode(hashlib.sha1(sign_str.encode()).digest()).decode()
    if signature != expected_signature:
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Декодуємо дані
    decoded_data = json.loads(base64.b64decode(data).decode())
    order_id = int(decoded_data["order_id"].split("_")[1])  # Отримуємо ID замовлення
    status = decoded_data["status"]

    # Оновлюємо статус замовлення в базі даних
    async with AsyncSessionLocal() as session:
        order = await session.get(Order, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        # Оновлюємо статус
        if status == "success" or status == "sandbox":
            order.status = "paid"
        elif status in ["failure", "error"]:
            order.status = "failed"
        else:
            order.status = status
        await session.commit()

        # Якщо оплата успішна
        if order.status == "paid":
            try:
                # Видаляємо повідомлення з кнопкою оплати
                if order.message_id:
                    await bot.delete_message(chat_id=order.user_id, message_id=order.message_id)
                # Надсилаємо сповіщення користувачу
                await bot.send_message(order.user_id, "✅ Оплата пройшла успішно, дякуємо за покупку!")
            except Exception as e:
                print(f"Error notifying user: {e}")

    return {"status": "ok"}