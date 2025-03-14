import base64
import json
import hashlib
import hmac
from bot.config import LIQPAY_PUBLIC_KEY, LIQPAY_PRIVATE_KEY, SERVER_URL

LIQPAY_API_URL = "https://www.liqpay.ua/api/3/checkout"

def generate_payment_link(total_price: float, order_id: str, description: str = "Оплата замовлення"):
    """Генерує посилання на оплату через LiqPay."""
    data = {
        "version": 3,
        "public_key": LIQPAY_PUBLIC_KEY,
        "action": "pay",
        "amount": float(f"{total_price:.2f}"),
        "currency": "UAH",
        "description": description,
        "order_id": order_id,
        "sandbox": 1,  # Увімкнення тестового режиму
        "result_url": "https://t.me/zagluska_bot",
        "server_url": f"{SERVER_URL}/payment-callback"  # URL обробки платежу
    }

    data_json = json.dumps(data)
    data_base64 = base64.b64encode(data_json.encode()).decode()

    sign_str = LIQPAY_PRIVATE_KEY + data_base64 + LIQPAY_PRIVATE_KEY
    signature = base64.b64encode(hashlib.sha1(sign_str.encode()).digest()).decode()
    payment_url = f"https://www.liqpay.ua/api/3/checkout?data={data_base64}&signature={signature}"

    print(f"Generated payment URL: {payment_url}")
    print(f"Data: {data_json}")
    print(f"Signature: {signature}")

    return payment_url