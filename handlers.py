import sys

# todo РОУТЕР ДЕЛАЙ ОБРАБОТКУ ДЛЯ АДМИНСКИХ КНОПОК

from bot import bot
from config import ADMIN_ID, OWNER_ID, PRICES, NUMBER, DAYS, BOT_LINK
from database import database_manager
from keyboards import (
	admin_menu_keyboard,
	cancel_keyboard,
	user_menu_keyboard,
	country_keyboard,
	buy_keyboard,
	temp_link_keyboard,
	status_keyboard,
	admin_approve_reject_keyboard,
)
from logger import logger
from telegram_helpers import (
	qrcode_generate,
	generate_secure_code,
	send_temp_photo,
	send_temp_message,
	temp_code_deleter,
	is_admin,
	is_work_time
)

from config import (
	BUY_BUTTON,
	TEMP_LINK_BUTTON,
	STATISTIC_BUTTON,
	AMDINS_LINK_BUTTON,
	REF_BUTTON,
	STATUS_BUTTON,
	HELP_BUTTON,
	LOCATION_BUTTON,
	BONUS)

from servers import server_manager

user_plan = {}
user_country = {}
temp_links = {}

def cancel_handler(call):
	bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
	bot.answer_callback_query(call.id)

def country_handler(call):
	user_id = call.from_user.id
	data = call.data
	country = data.split(":")[1]

	send_temp_message(bot, user_id, '⏳ Запрос обрабатывается', 5)
	bot.answer_callback_query(call.id)

	country_ids = server_manager.get_country_ids(country)
	servers_load = database_manager.get_servers_load(country_ids)
	min_server = min(servers_load, key=servers_load.get) # сервер с минимальным кол-вом юзером
	database_manager.update_user_server(user_id, min_server)

	bot.edit_message_text(f"Локация изменена: {country}", user_id, call.message.message_id, reply_markup=cancel_handler())


def ref_handler(message):
	user_id = message.from_user.id
	link = f'{BOT_LINK}?start={user_id}'
	bot.send_message(user_id, f'<code>{link}</code>', reply_markup=cancel_keyboard(), parse_mode='HTML')

def help_handler(message):
	user_id = message.from_user.id
	text = (
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
	bot.send_message(user_id, text, reply_markup=cancel_keyboard(), parse_mode='HTML' )

def plan_handler(call):
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

	bot.edit_message_text(message, user_id, call.message.message_id, reply_markup=cancel_keyboard(), parse_mode='HTML')
	bot.answer_callback_query(call.id)


def approved_handler(call):
	data = call.data.split(':')
	

	user_id = int(data[1])
	plan = int(data[2])
	send_temp_message(bot, user_id, '⏳ Запрос обрабатывается', 30)
	bot.answer_callback_query(call.id)

	result = database_manager.create_subscription(user_id, DAYS[plan])

	send_temp_message(bot, user_id, f'✅ Вы купили {DAYS[plan]} дней подписки', 120)

	if result is not None:
		inviter_id = result['inviter_id']
		send_temp_message(bot, inviter_id, F'✅ Бонус {BONUS} получен!', 30)

	bot.send_message(OWNER_ID, f'✅ Куплена подписка на сумму {PRICES.get(plan, "неизвестно")} ₽')
	info_message = """Сообщение исчезнет через 120 сек.\n
	Получить ссылку: <code>Меню</code> -> <code>Статус</code>\n
	❗️ Обязательно выберите локацию, если купили подписку впервые.\n"""

	send_temp_message(bot, user_id, info_message, 120, parse_mode='HTML')


def show_reject(call):
	user_id = int(call.data.split(':')[1]) 

	try:
		send_temp_message(bot, user_id, '❌ Оплата отклонена. Попробуйте ещё раз или свяжитесь с поддержкой.', 30)
	except Exception as e:
		logger.warning(f'Не удалось отправить сообщение пользователю {user_id}: {e}')

	try:
		bot.edit_message_caption(chat_id=ADMIN_ID, message_id=call.message.message_id, caption='❌ ОТКЛОНЕНО')
	except Exception as e:
		logger.warning(f'Не удалось отредактировать сообщение администратора: {e}')

	bot.answer_callback_query(call.id)


def temp_link_handler(call):
	plan = int(call.data.split(':')[1])

	bot.answer_callback_query(call.id)
	send_temp_message(bot, ADMIN_ID, '⏳ Запрос обрабатывается', 30)

	admin_server_id = database_manager.get_user_server_id(ADMIN_ID) # получаем id сервера админа

	api_client = get_api_server(admin_server_id) # получаем api clietn для сервера админа
	code = generate_secure_code(5)
	user_id = int(generate_secure_code(8))

	api_client.schedule_delete(user_id)

	temp_code_deleter(dict=temp_links, key=code, value=(user_id, plan))

	answer = api_client.create_user(user_id)

	if answer['status'] == "ok":
		vless_url = answer['link']
	else:
		send_temp_message(bot, ADMIN_ID, f"⚠️ Ошибка создания пользователя!", 120, parse_mode="HTML")
		api_client.delete_user(user_id)
		return

	send_qr_and_link(ADMIN_ID, vless_url)
	send_temp_message(bot, ADMIN_ID, f"Код пользователя: <code>{code}</code>", 120, parse_mode="HTML")
	api_client.schedule_delete(user_id)
	

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

	database_manager.create_new_user(user_id, referrer)

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
		plan = user_plan.pop(user_id)

		if not plan:
			bot.send_message(user_id, '❗ Сначала выбери тариф')
			return

		keyboard = admin_approve_reject_keyboard(user_id, plan)
		caption = f'🆕 Оплата\nUser: @{username}\nТариф: {plan} мес\n\nID: {user_id}'

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


@bot.message_handler(func=lambda m: True)
def router(message):
	text = message.text
	user_id = message.from_user.id
	
	if text == BUY_BUTTON:
		if is_work_time():
			bot.send_message(user_id, "Выберите тариф", reply_markup=buy_keyboard())
		else:
			send_temp_message(bot, user_id, "💤 Администратор спит, поппробуйте позже")

	if text == STATUS_BUTTON:
		paid_days = database_manager.get_paid_days(user_id)
		location_id = database_manager.get_user_server_id(user_id)
		country_conf = server_manager.get_country_by_server_id(location_id)
		country_name = country_conf.name
		if not is_admin(user_id):
			if paid_days > 0:
				bot.send_message(user_id, f"У вас осталось: {paid_days} д.\nЛокация: {country_name}", reply_markup=status_keyboard())
			else:
				bot.send_message(user_id, "У вас нет активной подписки", reply_markup=cancel_keyboard())
		else:
			bot.send_message(user_id, f"У вас осталось: {paid_days} д.\nЛокация: {country_name}", reply_markup=status_keyboard())
	
	if text == LOCATION_BUTTON:
		bot.send_message(user_id, "Выберите локацию", reply_markup=country_keyboard())

	if text == REF_BUTTON:
		ref_handler(message)
	
	if text == HELP_BUTTON:
		help_handler(message)

	if text == STATISTIC_BUTTON:
		bot.send_message(user_id, "В разработке")

	if text == AMDINS_LINK_BUTTON:
		bot.send_message(user_id, "В разработке")

	if text == TEMP_LINK_BUTTON:
		if is_admin(user_id):
			bot.send_message(user_id, "Выберите тарифк", reply_markup=temp_link_keyboard())		

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
	try:
		data = call.data

		if data == "cancel":
			cancel_handler(call)

		if data.startswith('country:'):
			country_handler(call)

		if data.startswith('plan:'):
			plan_handler(call)
			return
		
		if data.startswith('temp:'):
			temp_link_handler(call)
			return
		
		if data.startswith('approve:'):
			approved_handler(call)
			return
		
		if data.startswith('reject:'):
			show_reject(call)
			return
		
		if data == 'qr':
			user_id = call.from_user.id
			vless_url = load_user_link(user_id)
			buffer = qrcode_generate(vless_url)
			send_temp_photo(bot, user_id, buffer, 30, caption='Сообщение исчезнет через 30 сек.')
			bot.answer_callback_query(call.id)
			return
		
		if data == 'link':
			
			user_id = call.from_user.id
			vless_url = load_user_link(user_id)
			send_temp_message(bot, user_id, f'<code>{vless_url}</code>', 30, parse_mode='HTML')
			send_temp_message(bot, user_id, 'Сообщение исчезнет через 30 сек.', 30, parse_mode='HTML')
			bot.answer_callback_query(call.id)
			return
		
	except Exception as e:
		logger.error(f'Ошибка в callback: {e}')
