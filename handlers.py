import sys

from bot import bot
from config import ADMIN_ID, OWNER_ID, PRICES, NUMBER, DAYS, BOT_LINK
from database import Database
from keyboards import (
    admin_menu_keyboard,
    user_menu_keyboard,
    buy_keyboard,
    temp_link_keyboard,
    add_return_keyboard,
    status_keyboard,
    admin_approve_reject_keyboard,
)
from logger import logger
from telegram_helpers import (
    qrcode_generate,
    generate_secure_code,
    send_temp_photo,
    send_temp_message,
    temp_code_deleter
)
from xray import create_user, get_users_link, schedule_user_deletion, delete_users_link

try:
    db = Database()
except Exception as e:
    logger.error(f'Критическая ошибка инициализации БД: {e}')
    sys.exit(1)

user_plan = {}
temp_links = {}

def show_menu(call):
    user_id = call.from_user.id

    if user_id == ADMIN_ID:
        keyboard = admin_menu_keyboard()
    else:
        keyboard = user_menu_keyboard()

    bot.edit_message_text('Меню', user_id, call.message.message_id, reply_markup=keyboard)
    bot.answer_callback_query(call.id)


def show_temp_link_keyboard(call):
    keyboard = add_return_keyboard(temp_link_keyboard())
    bot.edit_message_text('Временная ссылка', ADMIN_ID, call.message.message_id, reply_markup=keyboard)
    bot.answer_callback_query(call.id)


def show_buy(call):
    user_id = call.from_user.id
    keyboard = add_return_keyboard(buy_keyboard())
    bot.edit_message_text('Купить подписку', user_id, call.message.message_id, reply_markup=keyboard)
    bot.answer_callback_query(call.id)


def show_status(call):
    user_id = call.from_user.id
    days = db.get_paid_days(user_id)

    if days == 0:
        bot.edit_message_text('❌ У вас нет активной подписки.\n', user_id, call.message.message_id, reply_markup=add_return_keyboard())
    else:
        message = f'✅ Дней до конца подписки: {days}.\n'
        keyboard = add_return_keyboard(status_keyboard())
        bot.edit_message_text(message, user_id, call.message.message_id, reply_markup=keyboard)

    bot.answer_callback_query(call.id)


def show_ref(call):
    user_id = call.from_user.id
    link = f'{BOT_LINK}?start={user_id}'
    bot.edit_message_text(f'Ваша реферальная ссылка: <code>{link}</code>', user_id, call.message.message_id, reply_markup=add_return_keyboard(), parse_mode='HTML')
    bot.answer_callback_query(call.id)


def show_help(call):
    user_id = call.from_user.id
    message = (
        '<b>📖 Инструкция по подключению</b>\n\n'
        'После покупки вы получите:\n'
        '• 🔗 персональную ссылку\n'
        '• 📱 QR-код для быстрого подключения\n\n'
        '<b>Как подключиться?</b>\n\n'
        '1️⃣ Установите клиент <b>V2Ray</b> на своё устройство.\n\n'
        '<b>📱 Android</b>\n'
        '<code>v2rayTun</code>\n\n'
        '<b>🍏 iPhone (iOS)</b>\n'
        '<code>v2ray</code>\n\n'
        '<b>🖥 Windows</b>\n'
        'https://github.com/2dust/v2rayN/releases \n\n'
        '2️⃣ Откройте приложение.\n\n'
        '3️⃣ Импортируйте полученную ссылку или отсканируйте QR-код.\n\n'
        '<b>❓ Возникли вопросы?</b>\n\n'
        'Напишите:\n'
        '<b>@Johan_Sundstain</b>'
    )

    bot.edit_message_text(message, user_id, call.message.message_id, reply_markup=add_return_keyboard(), parse_mode='HTML')
    bot.answer_callback_query(call.id)


def show_plan(call):
    user_id = call.from_user.id
    plan = int(call.data.split(':')[1])
    user_plan[user_id] = plan

    if plan == -1:
        message = '<b>Отправьте боту код в чат командой:</b>\n<code>/code КОД</code>\n'
    else:
        message = (
            f'<b>Вы выбрали:</b> {plan} мес.\n\n'
            f'<b>Оплата по номеру телефона:</b>\n'
            f'<code>+{NUMBER}</code>\n'
            '<b>Банки:</b> Сбер / ТБанк\n\n'
            'После оплаты отправьте <b>результат операции</b> '
            '(файл или скриншот) в чат бота.'
        )

    bot.edit_message_text(message, user_id, call.message.message_id, reply_markup=add_return_keyboard(), parse_mode='HTML')
    bot.answer_callback_query(call.id)


def show_approved(call):
    data = call.data.split(':')
    user_id = int(data[1])
    plan = int(data[2])
    is_update = db.get_paid_days(user_id) > 0
    db.create_subscription(user_id, DAYS[plan])

    if is_update:
        send_temp_message(bot, user_id, '✅ Подписка продлена.', 30)
    else:
        try:
            vless_url = create_user(user_id)
            send_qr_and_link(user_id, vless_url)
        except Exception as e:
            logger.error(f'Ошибка создания пользователя {user_id}: {e}')
            send_temp_message(bot, user_id, f'✅ Вы купили {DAYS[plan]} дней подписки', 30)

        try:
            bot.edit_message_caption(chat_id=ADMIN_ID, message_id=call.message.message_id, caption='✅ ПОДТВЕРЖДЕНО')
        except Exception as e:
            logger.warning(f'Не удалось отредактировать сообщение администратора: {e}')

    bot.send_message(OWNER_ID, f'✅ Куплена подписка на сумму {PRICES.get(plan, "неизвестно")} ₽')
    send_temp_message(bot, user_id, 'Сообщение исчезнет через 120 сек.\nПовторно получить ссылку: <code>Меню</code> -> <code>Статус</code>', 120, parse_mode='HTML')
    bot.answer_callback_query(call.id)


def show_reject(call):
    user_id, plan = map(int, call.data.split(':')[1:])

    try:
        send_temp_message(bot, user_id, '❌ Оплата отклонена. Попробуйте ещё раз или свяжитесь с поддержкой.', 30)
    except Exception as e:
        logger.warning(f'Не удалось отправить сообщение пользователю {user_id}: {e}')

    try:
        bot.edit_message_caption(chat_id=ADMIN_ID, message_id=call.message.message_id, caption='❌ ОТКЛОНЕНО')
    except Exception as e:
        logger.warning(f'Не удалось отредактировать сообщение администратора: {e}')

    bot.answer_callback_query(call.id)


def show_temp_link(call):
    plan = int(call.data.split(':')[1])
    code = generate_secure_code(5)
    user_id = int(generate_secure_code(8))
    temp_code_deleter(dict=temp_links, key=code, value=(user_id, plan))
    vless_url = create_user(user_id)
    
    send_qr_and_link(ADMIN_ID, vless_url)
    send_temp_message(bot, ADMIN_ID, f"Код пользователя: <code>{code}</code>", 120, parse_mode="HTML")
    schedule_user_deletion(user_id)
    
    bot.answer_callback_query(call.id)


def send_qr_and_link(user_id, url):
    if not url:
        logger.error(f'Не удалось создать ссылку для пользователя {user_id}')
        send_temp_message(bot, user_id, '⚠️ Ошибка генерации ссылки. Обратитесь в поддержку.', 30)
        return

    try:
        buffer = qrcode_generate(url)
        send_temp_photo(bot, user_id, buffer, 120)
        send_temp_message(bot, user_id, f'<code>{url}</code>', 120, parse_mode='HTML')
    except Exception as e:
        logger.error(f'Ошибка генерации QR-кода: {e}')
        send_temp_message(bot, user_id, '⚠️ Ошибка генерации ссылки. Обратитесь в поддержку.', 30)


@bot.message_handler(commands=['start'])
def start(message):
    args = message.text.split()
    user_id = message.from_user.id

    referrer = None
    if len(args) > 1:
        try:
            referrer = int(args[1])
            if referrer == user_id:
                referrer = None
        except ValueError:
            referrer = None

    db.create_new_user(user_id, referrer)

    try:
        if user_id == ADMIN_ID:
            keyboard = admin_menu_keyboard()
        else:
            keyboard = user_menu_keyboard()

        bot.send_message(user_id, 'Меню', reply_markup=keyboard)
    except Exception as e:
        logger.error(f'Ошибка в start: {e}')
        bot.send_message(user_id, '⚠️ Произошла ошибка. Попробуйте позже.')


@bot.message_handler(content_types=['photo', 'document', 'video'])
def handle_file_upload(message):
    try:
        user_id = message.from_user.id
        username = message.from_user.username or 'no_username'
        plan = user_plan.get(user_id)

        if not plan:
            bot.send_message(user_id, '❗ Сначала выбери тариф')
            return

        keyboard = admin_approve_reject_keyboard(user_id, plan)
        caption = f'🆕 Оплата\nUser: @{username}\nТариф: {plan} мес\nID: {user_id}'

        if message.content_type == 'photo':
            bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=caption, reply_markup=keyboard)
        elif message.content_type == 'document':
            bot.send_document(ADMIN_ID, message.document.file_id, caption=caption, reply_markup=keyboard)
        elif message.content_type == 'video':
            bot.send_video(ADMIN_ID, message.video.file_id, caption=caption, reply_markup=keyboard)
        else:
            bot.send_message(ADMIN_ID, caption + '\n\n❗ Неизвестный тип файла')

        try:
            bot.delete_message(user_id, message.message_id)
            logger.info(f'Сообщение пользователя {user_id} удалено')
        except Exception as e:
            logger.warning(f'Не удалось удалить сообщение пользователя: {e}')

        send_temp_message(bot, user_id, '⏳ Файл получен, ожидайте проверки', 30)
    except Exception as e:
        logger.error(f'Ошибка: {e}')
        bot.send_message(message.from_user.id, '⚠️ Ошибка обработки файла')


@bot.message_handler(commands=['code'])
def handle_code_command(message):
    try:
        parts = message.text.split()
        user_id = message.from_user.id

        if len(parts) < 2:
            warning = (
                '❌ Вы не ввели код!\n'
                '<br>📝 Использование</br>: <code>/code КОД</code>\n'
                '<br>Пример</br>: <code>/code A7K2P</code>'
            )
            send_temp_message(bot, user_id, warning, 30, parse_mode='HTML')
            return

        code = parts[1]
        if code in temp_links:
            temp_id, plan = temp_links.pop(code)
            delete_users_link(temp_id)
            db.create_subscription(user_id, DAYS[plan])
            send_temp_message(bot, user_id, '✅ Код активирован.', 30)
            vless_url = create_user(user_id)
            send_qr_and_link(user_id, vless_url)
        else:
            send_temp_message(bot, user_id, '❌ Неверный код!', 30)

        try:
            bot.delete_message(user_id, message.message_id)
            logger.info(f'Сообщение пользователя {user_id} удалено')
        except Exception as e:
            logger.warning(f'Не удалось удалить сообщение пользователя: {e}')
    except Exception as e:
        logger.error(f'Ошибка: {e}')
        bot.send_message(message.from_user.id, '⚠️ Ошибка обработки кода')


@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    try:
        data = call.data
        if data == 'menu':
            show_menu(call)
            return

        if data == 'buy':
            show_buy(call)
            return
        
        if data == 'status':
            show_status(call)
            return
        
        if data == 'ref':
            show_ref(call)
            return
        
        if data == 'help':
            show_help(call)
            return
        
        if data.startswith('plan:'):
            show_plan(call)
            return
        
        if data == 'temp_link':
            show_temp_link_keyboard(call)
            return
        
        if data.startswith('temp:'):
            show_temp_link(call)
            return
        
        if data.startswith('approve:'):
            show_approved(call)
            return
        
        if data.startswith('reject:'):
            show_reject(call)
            return
        
        if data == 'qr':
            user_id = call.from_user.id
            vless_url = get_users_link(user_id)
            buffer = qrcode_generate(vless_url)
            send_temp_photo(bot, user_id, buffer, 30, caption='Сообщение исчезнет через 30 сек.')
            bot.answer_callback_query(call.id)
            return
        
        if data == 'link':
			
            user_id = call.from_user.id
            vless_url = get_users_link(user_id)
            send_temp_message(bot, user_id, f'<code>{vless_url}</code>', 30, parse_mode='HTML')
            send_temp_message(bot, user_id, 'Сообщение исчезнет через 30 сек.', 30, parse_mode='HTML')
            bot.answer_callback_query(call.id)
            return
        
    except Exception as e:
        logger.error(f'Ошибка в callback: {e}')
