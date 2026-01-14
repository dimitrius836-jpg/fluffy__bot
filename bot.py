import os
import re
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters
)

# === Настройки из переменных окружения ===
BOT_TOKEN = os.getenv("8511383858:AAFpbLiNLnCuOXrGwo03jQS4D6GKOUSFLbM")
YOUR_TELEGRAM_ID = int(os.getenv("202598362"))

# === Список промокодов (регистронезависимый) ===
VALID_PROMOCODES = {f"fly{i}" for i in range(1, 8)}  # fly1 ... fly7

# === Состояния диалога ===
(
    AGREEMENT,
    PROMOCODE,
    FULL_NAME,
    PHONE,
    ADDRESS,
    CONFIRM
) = range(6)

# === Валидация телефона ===
def validate_phone(phone: str) -> bool:
    # Убираем все пробелы и проверяем по маске
    cleaned = re.sub(r'\D', '', phone)  # оставляем только цифры
    return len(cleaned) == 11 and cleaned.startswith('7')

def format_phone(phone: str) -> str:
    # Приводим к виду: +7 (999) 123-45-67
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 11 and digits.startswith('7'):
        return f"+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"
    return phone  # fallback

# === Обработчики ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    policy_url = "https://disk.yandex.ru/i/ВАША_ССЫЛКА_НА_ПОЛИТИКУ"  # ← ЗАМЕНИТЕ!
    text = (
        "🦋 Добро пожаловать в Fluffy!\n\n"
        "У нас вы можете получить живых бабочек прямо к себе домой.\n\n"
        f"Ознакомьтесь с [политикой обработки персональных данных]({policy_url}).\n\n"
        "Нажмите кнопку ниже, чтобы продолжить:"
    )
    keyboard = [["✅ Соглашаюсь"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    return AGREEMENT

async def agreement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "✅ Соглашаюсь":
        await update.message.reply_text("Отлично! Пожалуйста, введите ваш промокод:")
        return PROMOCODE
    else:
        await update.message.reply_text("Пожалуйста, нажмите «✅ Соглашаюсь», чтобы продолжить.")
        return AGREEMENT

async def check_promocode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_code = update.message.text.strip().lower()
    if user_code in VALID_PROMOCODES:
        context.user_data["promocode"] = user_code
        await update.message.reply_text("Промокод принят! Теперь введите ваше ФИО:")
        return FULL_NAME
    else:
        await update.message.reply_text(
            "❌ Промокод не найден. Попробуйте снова:",
            reply_markup=ReplyKeyboardMarkup([["💬 Написать менеджеру"]], resize_keyboard=True)
        )
        return PROMOCODE

async def contact_manager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Свяжитесь с нами: https://t.me/butterfly_fluffy")
    return PROMOCODE

async def full_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text("Пожалуйста, введите корректное ФИО.")
        return FULL_NAME
    context.user_data["full_name"] = name
    await update.message.reply_text("Теперь введите ваш телефон в формате: +7 (999) 123-45-67")
    return PHONE

async def phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone_text = update.message.text.strip()
    if validate_phone(phone_text):
        formatted = format_phone(phone_text)
        context.user_data["phone"] = formatted
        await update.message.reply_text("Укажите адрес доставки:")
        return ADDRESS
    else:
        await update.message.reply_text(
            "Неверный формат телефона. Пожалуйста, используйте: +7 (999) 123-45-67"
        )
        return PHONE

async def address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    addr = update.message.text.strip()
    if not addr:
        await update.message.reply_text("Пожалуйста, укажите адрес доставки.")
        return ADDRESS
    context.user_data["address"] = addr

    # Подтверждение
    data = context.user_data
    confirm_text = (
        "Проверьте ваши данные:\n\n"
        f"ФИО: {data['full_name']}\n"
        f"Телефон: {data['phone']}\n"
        f"Адрес: {data['address']}\n\n"
        "Всё верно?"
    )
    keyboard = [["✅ Верно", "🔁 Изменить"]]
    await update.message.reply_text(
        confirm_text,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return CONFIRM

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    if "Верно" in choice:
        # Отправляем вам в Telegram
        data = context.user_data
        user_id = update.effective_user.id
        admin_msg = (
            f"🆕 Новая заявка!\n"
            f"ID: {user_id}\n"
            f"ФИО: {data['full_name']}\n"
            f"Телефон: {data['phone']}\n"
            f"Адрес: {data['address']}\n"
            f"Промокод: {data['promocode']}"
        )
        try:
            await context.bot.send_message(chat_id=YOUR_TELEGRAM_ID, text=admin_msg)
        except Exception as e:
            logging.error(f"Не удалось отправить админу: {e}")

        # Ответ пользователю
        await update.message.reply_text(
            "Спасибо за заказ! 🦋\n"
            "В ближайшее время мы отправим вам куколки бабочек.\n\n"
            "Если возникнут вопросы — напишите менеджеру: https://t.me/butterfly_fluffy",
            reply_markup=ReplyKeyboardMarkup([["❓ FAQ"]], resize_keyboard=True)
        )
        return ConversationHandler.END

    elif "Изменить" in choice:
        await update.message.reply_text("Хорошо, давайте введём данные заново.\nВведите ваше ФИО:")
        return FULL_NAME
    else:
        await update.message.reply_text("Пожалуйста, выберите вариант ниже.")
        return CONFIRM

async def faq_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ Часто задаваемые вопросы:\n\n"
        "• Доставка занимает 3–5 дней.\n"
        "• Бабочки приходят в специальных контейнерах.\n"
        "• Подробнее — в канале: https://t.me/butterfly_fluffy"
    )

# === Запуск ===
def main():
    logging.basicConfig(level=logging.INFO)
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AGREEMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, agreement)],
            PROMOCODE: [
                MessageHandler(filters.Regex("^💬 Написать менеджеру$"), contact_manager),
                MessageHandler(filters.TEXT & ~filters.COMMAND, check_promocode)
            ],
            FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, full_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone)],
            ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, address)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm)]
        },
        fallbacks=[]
    )

    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.Regex("^❓ FAQ$"), faq_handler))

    application.run_polling()

if __name__ == "__main__":
    main()