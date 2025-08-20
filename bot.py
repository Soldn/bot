import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from mcrcon import MCRcon

API_TOKEN = "YOUR_BOT_TOKEN"
ADMIN_ID = 7301372531
RCON_HOST = "95.216.92.87"
RCON_PORT = 25821
RCON_PASSWORD = "1kbgthcjjkK"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

DONATES = {
    "Iron": 19,
    "Gold": 49,
    "Diamond": 99,
    "Solar": 199
}

# Храним заявки
pending_orders = {}

@dp.message_handler(commands=["start"])
async def start_command(message: types.Message):
    await message.answer("Привет! Если хочешь купить донат, нажми кнопку на сайте, и бот пришлёт инструкцию.")

@dp.message_handler(lambda m: m.text and m.text.startswith("Хочу купить донат"))
async def handle_buy_request(message: types.Message):
    try:
        parts = message.text.split("Мой ник:")
        donate_info = parts[0].replace("Хочу купить донат", "").strip().split(", его цена")
        donate_name = donate_info[0].strip()
        nick = parts[1].strip()
    except Exception:
        await message.answer("Ошибка: не удалось разобрать сообщение. Напиши администратору.")
        return

    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("Я оплатил", callback_data=f"paid:{donate_name}:{nick}"))
    await message.answer(
        f"Спасибо, что хотите купить донат у нас ❤️

"
        f"📌 Ваш донат: {donate_name}
"
        f"👤 Ник: {nick}

"
        f"🇺🇦 Украина: 4441 1111 6434 7431
"
        f"🇷🇺 Россия: https://www.donationalerts.com/r/mrronny

"
        f"После оплаты нажмите кнопку ниже 👇",
        reply_markup=kb
    )

@dp.callback_query_handler(lambda c: c.data.startswith("paid:"))
async def process_paid(callback: types.CallbackQuery):
    _, donate, nick = callback.data.split(":")
    order_id = f"{callback.from_user.id}_{donate}_{nick}"
    pending_orders[order_id] = {"donate": donate, "nick": nick}

    await callback.message.answer("Пришлите скриншот/чек об оплате 👇")

@dp.message_handler(content_types=["photo"])
async def handle_payment_proof(message: types.Message):
    for order_id, data in list(pending_orders.items()):
        if str(message.from_user.id) in order_id:
            donate, nick = data["donate"], data["nick"]
            kb = InlineKeyboardMarkup().add(
                InlineKeyboardButton("✅ Одобрить", callback_data=f"approve:{order_id}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"decline:{order_id}")
            )
            await bot.send_photo(
                ADMIN_ID, photo=message.photo[-1].file_id,
                caption=f"Заявка на донат:

👤 Ник: {nick}
🎁 Донат: {donate}",
                reply_markup=kb
            )
            await message.answer("Ваш чек отправлен на проверку администратору ✅")
            return

@dp.callback_query_handler(lambda c: c.data.startswith("approve:") or c.data.startswith("decline:"))
async def process_admin_action(callback: types.CallbackQuery):
    action, order_id = callback.data.split(":")
    data = pending_orders.get(order_id)

    if not data:
        await callback.answer("Заявка не найдена.", show_alert=True)
        return

    donate, nick = data["donate"], data["nick"]
    user_id = int(order_id.split("_")[0])

    if action == "approve":
        try:
            with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
                mcr.command(f"lp user {nick} parent add {donate}")
            await bot.send_message(user_id, f"✅ Донат {donate} успешно выдан на аккаунт {nick}!")
        except Exception as e:
            await bot.send_message(user_id, f"❌ Ошибка выдачи доната. Обратитесь к админу @Soldi_n
Ошибка: {e}")
    else:
        await bot.send_message(user_id, "❌ Покупка доната отклонена. Свяжитесь с админом @Soldi_n")

    del pending_orders[order_id]
    await callback.message.edit_reply_markup()

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
