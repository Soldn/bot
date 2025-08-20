import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from mcrcon import MCRcon

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
ADMIN_TAG = os.getenv("ADMIN_TAG")
RCON_HOST = os.getenv("RCON_HOST")
RCON_PORT = int(os.getenv("RCON_PORT"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

DONATES = {
    "Iron": 19,
    "Prince": 39,
    "Legend": 99,
    "Wither": 199,
    "Berserk": 399,
    "Solar": 799,
}

# Временное хранилище заявок: user_id -> (donate, nick)
pending_orders = {}

@dp.message_handler(lambda m: m.text and m.text.startswith("Хочу купить донат"))
async def buy_donate(message: types.Message):
    try:
        parts = message.text.split(",")
        donate_name = parts[0].split("донат")[1].strip()
        nick = parts[2].split(":")[1].strip().replace("}", "")
        price = DONATES.get(donate_name)

        if not price:
            await message.reply("❌ Ошибка: неизвестный донат.")
            return

        text = f"""Спасибо что хотите купить товар именно у нас!\n
Если вы проживаете на территории Украины то скидывать сюда сумму: 4441 1111 6434 7431\n
Если вы проживаете на территории России то скидывать сюда: https://www.donationalerts.com/r/mrronny\n\n
Стоимость {donate_name} = {price}₽\n
Ваш ник: {nick}\n
"""

        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid:{donate_name}:{nick}"))
        await message.answer(text, reply_markup=keyboard)

    except Exception as e:
        await message.reply("⚠ Ошибка при обработке покупки.")
        logging.error(e)

@dp.callback_query_handler(lambda c: c.data.startswith("paid:"))
async def process_payment(callback: types.CallbackQuery):
    _, donate, nick = callback.data.split(":")
    user_id = callback.from_user.id
    pending_orders[user_id] = (donate, nick)
    await bot.send_message(user_id, "📸 Прикрепите скриншот или чек об оплате.")

@dp.message_handler(content_types=["photo"])
async def handle_screenshot(message: types.Message):
    if message.from_user.id not in pending_orders:
        await message.reply("⚠ У вас нет активных заказов.")
        return

    donate, nick = pending_orders[message.from_user.id]
    caption = f"🛒 Покупка доната {donate} для ника {nick}\nОт {message.from_user.full_name} (@{message.from_user.username})"

    # Кнопки для админа
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("✅ Одобрить", callback_data=f"approve:{message.from_user.id}:{donate}:{nick}"),
        types.InlineKeyboardButton("❌ Отклонить", callback_data=f"decline:{message.from_user.id}:{donate}:{nick}")
    )

    await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=caption, reply_markup=keyboard)
    await message.reply("📤 Ваш чек отправлен администратору на проверку.")

@dp.callback_query_handler(lambda c: c.data.startswith("approve:") or c.data.startswith("decline:"))
async def admin_action(callback: types.CallbackQuery):
    action, user_id, donate, nick = callback.data.split(":")
    user_id = int(user_id)

    if action == "approve":
        try:
            with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
                mcr.command(f"lp user {nick} parent add {donate}")
            await bot.send_message(user_id, f"✅ Донат {donate} успешно выдан на ник {nick}. Спасибо за покупку!")
            await callback.message.edit_caption(f"✅ Подтверждено. Донат {donate} выдан {nick}.")
        except Exception as e:
            await bot.send_message(user_id, "⚠ Ошибка выдачи доната. Свяжитесь с администратором.")
            await callback.message.edit_caption(f"⚠ Ошибка при выдаче доната {donate} для {nick}.")
            logging.error(e)

    elif action == "decline":
        await bot.send_message(user_id, f"❌ Покупка доната {donate} не подтверждена. Свяжитесь с администратором {ADMIN_TAG}.")
        await callback.message.edit_caption(f"❌ Администратор отклонил покупку доната {donate} для {nick}.")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
