from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.database.models import Product


def get_products_keyboard(products):
    keyboard = InlineKeyboardBuilder()
    for product in products:
        keyboard.row(
            InlineKeyboardButton(
                text=f"{product.name} - {product.price} грн",
                callback_data=f"product_{product.id}"
            )
        )
    return keyboard.as_markup()


def get_product_details_keyboard(product_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 На головну", callback_data="products")],
        [InlineKeyboardButton(text="💳 Купити", callback_data=f"buy_{product_id}")]
    ])


def get_product_variants_keyboard(product: Product):
    builder = InlineKeyboardBuilder()

    # Отримуємо варіанти товару з поля `types`
    for variant in product.types:
        builder.button(text=variant, callback_data=f"variant_{product.id}_{variant}")

    return builder.as_markup()