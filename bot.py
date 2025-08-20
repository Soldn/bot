import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from mcrcon import MCRcon
import os

# --- Конфиг ---
TOKEN = os.getenv("BOT_TOKEN", "ТВОЙ_ТОКЕН")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7301372531"))

RCON_HOST = os.getenv("RCON_HOST", "95.216.92.87")
RCON_PORT = int(os.getenv("RCON_PORT", "25821"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD", "1kbgthcjjkK")

DONATES = {
    "Iron": 19,
    "Prince": 39,
    "Legend": 99,
    "Wither": 199,
    "Berserk": 399,
    "Solar": 799
}

# --- Лог ---
logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# --- Парсинг сообщений от сайта ---
@dp.message_handler(lambda message: message.text.startswith("Хочу купить донат"))
async def handle_buy_request(message: types.Message):
    try:
        text = message.text
        donate = None
        nick = None

        for d in DONATES.keys():
            if f"донат {d}" in text:
                donate = d
                break

        if "Мой ник:" in text:
            nick = text.split("Мой ник:")[1].strip().replace(".", "")

        if not donate or not nick:
            await message.reply("Не удалось распознать донат или ник. Проверьте сообщение.")
            return

        message.conf = {"donate": donate, "nick": nick}

        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("Я оплатил ✅", callback_data=f"paid:{donate}:{nick}"))

        await message.reply(
            f"Спасибо, что хотите купить у нас донат!\n\n"
            f"📌 Донат: {donate}\n"
            f"💰 Цена: {DONATES[donate]}₽\n"
            f"👤 Ник: {nick}\n\n"
            "Если вы из Украины 🇺🇦 — переведите сюда: `4441 1111 6434 7431`\n"
            "Если вы из России 🇷🇺 — оплатите тут: https://www.donationalerts.com/r/mrronny",
            reply_markup=kb,
            parse_mode="Markdown"
        )

    except Exception as e:
        await message.reply(f"Ошибка: {e}")

@dp.callback_query_handler(lambda c: c.data.startswith("paid:"))
async def handle_paid(callback: types.CallbackQuery):
    _, donate, nick = callback.data.split(":")
    await callback.message.answer("Прикрепите скрин или чек об оплате 🧾")
    await bot.send_message(ADMIN_ID,
        f"🆕 Новый запрос оплаты!\n\n"
        f"👤 Ник: {nick}\n"
        f"💎 Донат: {donate}\n"
        f"💰 Цена: {DONATES[donate]}₽\n\n"
        f"Ожидается скрин оплаты."
    )

@dp.message_handler(content_types=['photo', 'document'])
async def handle_payment_proof(message: types.Message):
    if message.reply_to_message and "Прикрепите скрин" in message.reply_to_message.text:
        await message.forward(ADMIN_ID)
        await bot.send_message(ADMIN_ID,
            f"Покупатель {message.from_user.username or message.from_user.id} отправил чек."
        )

        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton("✅ Одобрить", callback_data=f"approve:{message.from_user.id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"decline:{message.from_user.id}")
        )
        await bot.send_message(ADMIN_ID, "Подтвердите или отклоните оплату:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("approve:"))
async def approve_payment(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    await bot.send_message(user_id, "✅ Оплата успешно подтверждена!\nДонат выдан 🎉")
    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            nick, donate = "TEST", "Iron"  # ⚠️ временно
            mcr.command(f"lp user {nick} parent add {donate}")
    except Exception as e:
        await bot.send_message(ADMIN_ID, f"Ошибка RCON: {e}")

@dp.callback_query_handler(lambda c: c.data.startswith("decline:"))
async def decline_payment(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    await bot.send_message(user_id, "❌ Оплата не подтверждена. Попробуйте позже или свяжитесь с админом @Soldi_n")
    await callback.answer("Отказ отправлен пользователю.")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
