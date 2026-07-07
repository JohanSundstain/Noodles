import sys

from bot import bot
from config import ADMIN_ID, OWNER_ID, PRICES, NUMBER, DAYS, BOT_LINK
from database import database_manager
from servers import server_manager
from workers import task_manager

from tasks import (
	switch_country_task,
	create_subscription,
	get_and_send_link,
	create_temp_link,
	send_user_stat,
	broadcast
)

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
from utils import (
	qrcode_generate,
	generate_secure_code,
	send_temp_photo,
	send_temp_message,
	temp_code_deleter,
	is_admin,
	is_owner,
	is_work_time,
	temp_codes
)

from config import (
	BUY_BUTTON,
	TEMP_LINK_BUTTON,
	STATISTIC_BUTTON,
	REF_BUTTON,
	STATUS_BUTTON,
	HELP_BUTTON,
	LOCATION_BUTTON,
	BONUS)


user_plan = {} # юзер id: выбранный им план 

def cancel_handler(call):
	bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
	bot.answer_callback_query(call.id)


def country_handler(call):
	bot.answer_callback_query(call.id)
	task_manager.set_task(switch_country_task, call)


def link_handler(call):
	bot.answer_callback_query(call.id)
	task_manager.set_task(get_and_send_link, call)


def ref_handler(message):
	user_id = message.from_user.id
	link = f'{BOT_LINK}?start={user_id}'
	bot.send_message(user_id, f'<code>{link}</code>', reply_markup=cancel_keyboard(), parse_mode='HTML')


def status_handler(message):
	user_id = message.from_user.id
	task_manager.set_task(send_user_stat, user_id)


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
	bot.answer_callback_query(call.id)
	data = call.data.split(':')
	user_id = int(data[1])
	plan = int(data[2])

	send_temp_message(bot, call.from_user.id, '⏳ Запрос обрабатывается...', 30)
	task_manager.set_task(create_subscription, user_id=user_id, plan=plan, call=call)
	

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
	bot.answer_callback_query(call.id)
	task_manager.set_task(create_temp_link, call)
	

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
		if code in temp_codes:
			""" Если код верен, создаем пользователю подписку с его планом"""
			plan = temp_codes.pop(code, None)
			task_manager.set_task(create_subscription, user_id=user_id, plan=plan)
			send_temp_message(bot, user_id, '✅ Код активирован.', 30, reply_markup=user_menu_keyboard())
		else:
			send_temp_message(bot, user_id, '❌ Неверный код!', 30, reply_markup=user_menu_keyboard())

		try:
			bot.delete_message(user_id, message.message_id)
			logger.info(f'Сообщение пользователя {user_id} удалено')
		except Exception as e:
			logger.warning(f'Не удалось удалить сообщение пользователя: {e}')
		
		
	except Exception as e:
		logger.error(f'Ошибка: {e}')
		bot.send_message(message.from_user.id, '⚠️ Ошибка обработки кода')


@bot.message_handler(commands=['all'])
def handle_all_command(message):
	try:
		parts = message.text.split()
		user_id = message.from_user.id
		if is_owner(user_id) or is_admin(user_id):
			if len(parts) < 2:
				warning = (
					'❌ Вы не ввели сообщение!\n'
					'<br>📝 Использование</br>: <code>/all СООБЩЕНИЕ</code>\n'
					'<br>Пример</br>: <code>/all Всем привет!</code>'
				)
				send_temp_message(bot, user_id, warning, 30, parse_mode='HTML')
				return

			all_message = " ".join(parts[1:])

			task_manager.set_task(broadcast, all_message)

	except Exception as e:
		logger.error(f'Ошибка: {e}')
		bot.send_message(message.from_user.id, '⚠️ Ошибка обработки кода')


@bot.message_handler(commands=['info'])
def handle_inf_command(message):
	
	from owner_funcs import get_info

	parts = message.text.split()
	user_id = int(parts[1])
	if is_owner(message.from_user.id):
		task_manager.set_task(get_info, user_id)


@bot.message_handler(commands=['switch'])
def handle_switch_command(message):
	
	from owner_funcs import set_server

	parts = message.text.split()
	user_id = int(parts[1])
	serv_id = parts[2]
	if is_owner(message.from_user.id):
		task_manager.set_task(set_server, user_id, serv_id)
		

@bot.message_handler(commands=['reduce'])
def handle_reduce_command(message):
	
	from owner_funcs import reduce_days

	parts = message.text.split()
	user_id = int(parts[1])
	days = int(parts[2])
	if is_owner(message.from_user.id):
		task_manager.set_task(reduce_days, user_id, days)
	


	

@bot.message_handler(func=lambda m: True)
def router(message):
	text = message.text
	user_id = message.from_user.id
	
	if text == BUY_BUTTON:
		if is_work_time():
			bot.send_message(user_id, "Выберите тариф", reply_markup=buy_keyboard())
		else:
			send_temp_message(bot, user_id, "💤 Администратор спит, поппробуйте позже")
		return

	if text == STATUS_BUTTON:
		status_handler(message)
		return
	
	if text == LOCATION_BUTTON:
		bot.send_message(user_id, "Выберите локацию", reply_markup=country_keyboard())
		return

	if text == REF_BUTTON:
		ref_handler(message)
		return
	
	if text == HELP_BUTTON:
		help_handler(message)
		return

	if text == STATISTIC_BUTTON:
		bot.send_message(user_id, "В разработке")
		return

	if text == TEMP_LINK_BUTTON:
		if is_admin(user_id):
			bot.send_message(user_id, "Выберите тарифк", reply_markup=temp_link_keyboard())	
		return	


@bot.callback_query_handler(func=lambda call: True)
def callback(call):
	try:
		data = call.data

		if data == "cancel":
			cancel_handler(call)
			return

		if data.startswith('country:'):
			country_handler(call)
			return

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
		
		if data == 'link':
			link_handler(call)
			return
		
	except Exception as e:
		logger.error(f'Ошибка в callback: {e}')
