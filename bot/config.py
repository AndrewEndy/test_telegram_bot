import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
LIQPAY_PUBLIC_KEY = os.getenv("LIQPAY_PUBLIC_KEY")
LIQPAY_PRIVATE_KEY = os.getenv("LIQPAY_PRIVATE_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
ADMINS = [int(admin_id) for admin_id in os.getenv("ADMINS").split(',')]
SERVER_URL = os.getenv("SERVER_URL")