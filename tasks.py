from servers import server_manager
from database import database_manager
from telebot.apihelper import ApiTelegramException
import time
from datetime import datetime, timezone

from utils import (
	qrcode_generate,
	send_temp_message,
	send_temp_photo,
	logger,
	generate_secure_code,
	temp_code_deleter,
	is_admin,
	is_owner
)

from keyboards import(
	status_keyboard,
	country_keyboard
)

from config import (
	ADMIN_ID,
	OWNER_ID,
	DAYS,
	BONUS,
	PRICES
)

from bot import bot

from keyboards import (
	cancel_keyboard
)

def broadcast(text):
	user_ids = database_manager.get_all_user_ids()
	for user_id in user_ids:
		try:
			bot.send_message(user_id, text)
			time.sleep(0.05)  # ~20 msg/sec безопасно

		except ApiTelegramException as e:
			print(f"Error for {user_id}: {e}")

		except Exception as e:
			print(f"Unexpected error for {user_id}: {e}")


locations = {} # {user_id : {new_user_server_id, prev_user_server_id, new_user_backup_id, prev_user_backup_id}}
def selection_of_locations(call):
	global locations
	user_id = call.from_user.id
	country = call.data.split(":")[1]
	type = call.data.split(":")[2]
	if user_id not in locations: 
		locations[user_id] = {}
	if type == "main":
		country_ids = server_manager.get_country_ids(country) # получаем все серверы данной страны
		servers_load = database_manager.get_servers_load(country_ids) # получам загрузку каждого сервера
		new_server_id = min(servers_load, key=servers_load.get) # сервер с минимальным кол-вом юзером

		"""Запоминаем изменения основных серверов"""
		locations[user_id]['new_user_server_id'] = new_server_id
		locations[user_id]['prev_user_server_id'] = database_manager.get_user_server_id(user_id)
		bot.edit_message_text( "✈️ Выберите резервную локацию", call.message.chat.id, call.message.message_id, reply_markup=country_keyboard(country))
	else:
		country_ids = server_manager.get_country_ids(country) # получаем все серверы данной страны
		servers_load = database_manager.get_servers_load(country_ids, main=False) # получам загрузку каждого сервера
		new_backup_id = min(servers_load, key=servers_load.get) # сервер с минимальным кол-вом юзером

		"""Запоминаем изменения резервных серверов"""
		locations[user_id]['new_user_backup_id'] = new_backup_id
		locations[user_id]['prev_user_backup_id'] = database_manager.get_user_server_id(user_id, main=False)

		switch_country_task(call)


def switch_country_task(call):
	global locations
	user_id = call.from_user.id
	user_id_str = str(user_id)
	if is_admin(user_id) or is_owner(user_id):
		database_manager.update_user_server(user_id, locations[user_id]['new_user_server_id']) # обновляем страну мэйна в базе
		database_manager.update_user_server(user_id, locations[user_id]['new_user_backup_id'], main=False) # обновляем страну бэкапа в базе
		admin_message = f""" ✅ Локации изменены.\n
				⛓️ Получить ссылки: <code>Статус</code>"""
		
		bot.edit_message_text(admin_message,
					call.message.chat.id, 
					call.message.message_id,
					reply_markup=cancel_keyboard(),
					parse_mode='HTML')
	else:
		paid_days = database_manager.get_paid_days(user_id)
		if paid_days > 0:
			database_manager.update_user_server(user_id, locations[user_id]['new_user_server_id']) # обновляем страну мэйна в базе
			database_manager.update_user_server(user_id, locations[user_id]['new_user_backup_id'], main=False) # обновляем страну бэкапа в базе

			new_main_api_client = server_manager.get_api_server(locations[user_id]['new_user_server_id'])
			new_backup_api_client = server_manager.get_api_server(locations[user_id]['new_user_backup_id'])

			answer_main = new_main_api_client.user_exists(user_id_str)
			if not answer_main['exists']:
				query = new_main_api_client.create_user(user_id_str)
				if query['status'] != 'ok':
					bot.edit_message_text(f"❌ Ошибка создания пользователя.", call.message.chat.id,  call.message.message_id, reply_markup=cancel_keyboard())
					return

			answer_backup = new_backup_api_client.user_exists(user_id_str)
			if not answer_backup['exists']:
				query = new_backup_api_client.create_user(user_id_str)
				if query['status'] != 'ok':
					bot.edit_message_text(f"❌ Ошибка создания пользователя.", call.message.chat.id,  call.message.message_id, reply_markup=cancel_keyboard())
					return
				
			user_message = f""" ✅ Локации изменены.\n
				❗️Старые ссылки будут удалены.\n
				⛓️ Получить ссылки: <code>Статус</code>."""
			bot.edit_message_text(user_message, call.message.chat.id, call.message.message_id, reply_markup=cancel_keyboard(), parse_mode='HTML')
		else:
			message = f"❌ Сначала оформите подписку."
			bot.edit_message_text(message, call.message.chat.id, call.message.message_id, reply_markup=cancel_keyboard())

	locations.pop(user_id, None)	


def get_and_send_link(call):
	send_temp_message(bot, call.from_user.id, "⏳ Генерация ссылки...")

	user_id = call.from_user.id
	user_id_str = str(user_id)
	link_type = call.data.split(":")[1]

	if link_type == "main":
		user_server_id = database_manager.get_user_server_id(user_id) # получаем id сервера пользователя
	else:
		user_server_id = database_manager.get_user_server_id(user_id, main=False)
	
	if user_server_id == 'none': # если не выбрана локация, то отказываем в генерации
		bot.delete_message(user_id, call.message.message_id)
		send_temp_message(bot, user_id, "❌ Не выбрана локация.", 30)
		return

	user_api_client = server_manager.get_api_server(user_server_id) # получаем апи клиент к серверу юзера

	if is_admin(user_id) or is_owner(user_id):
		answer =  user_api_client.get_link("main")
	else:
		answer = user_api_client.get_link(user_id_str)

	if answer["status"] == "ok":
		vless_url = answer["link"]
		buffer = qrcode_generate(vless_url)
		send_temp_photo(bot, user_id, buffer, 30, caption=f'<code>{vless_url}</code>', parse_mode='HTML')
	else:
		send_temp_message(bot, user_id, "❌ Проблемы с сервером, обратитесь в поддержку.", 30)
		logger.error(f"Ошибка получения ссылки от сервера {answer['details']}")


def create_subscription(user_id=None, plan=None, call=None):

	result = database_manager.create_subscription(user_id, DAYS[plan])
	database_manager.create_transaction(user_id, PRICES[plan])

	send_temp_message(bot, user_id, f'✅ Вы купили {DAYS[plan]} дней подписки', 120)

	if result is not None:
		inviter_id = result['inviter_id']
		bot.send_message(inviter_id, f'✅ Бонус {BONUS} д. получен!')

	bot.send_message(OWNER_ID, f'✅ Куплена подписка на сумму {PRICES.get(plan, "неизвестно")} ₽')
	info_message = """Сообщение исчезнет через 120 сек.\n
	Получить ссылку: <code>Статус</code>\n
	❗️ Обязательно выберите локацию, если купили подписку впервые.\n"""

	send_temp_message(bot, user_id, info_message, 120, parse_mode='HTML')

	if call is not None:
		message_id = call.message.message_id
		text = f"""✅ ПОДТВЕРЖДЕНО\n
		<b>ID: <code>{user_id}</code></b>
		<b>Plan: <code>{DAYS[plan]}</code></b>"""
		bot.edit_message_caption(text, ADMIN_ID, message_id, parse_mode="HTML")


def create_temp_link(call):
	user_id = call.from_user.id
	user_id_str = str(user_id)

	if is_admin(user_id) or is_owner(user_id):
		send_temp_message(bot, user_id, '⏳ Запрос обрабатывается...', 30)

		plan = call.data.split(":")[1]
		admin_server_id = database_manager.get_user_server_id(user_id) # получаем id сервера админа

		if admin_server_id == 'none': # админ не выбрал локацию
			send_temp_message(bot, user_id, "❌ Не выбрана локация.", 30)
			return 
		
		api_client = server_manager.get_api_server(admin_server_id) # получаем api клиента для сервера админа

		answer = api_client.get_temp_link(user_id_str) # делаем запрос на сервер, чтобы создать временную ссылку
	
		if answer["status"] == "ok":
			vless_url = answer['link']
			code = generate_secure_code(6)
			temp_code_deleter(code, int(plan))
			buffer = qrcode_generate(vless_url)
			send_temp_photo(bot, user_id, buffer, 120, caption=f'<code>{vless_url}</code>', parse_mode='HTML')
			send_temp_message(bot, user_id, f"Код: <code>{code}</code>", 120, parse_mode="HTML")
		else:
			send_temp_message(bot, user_id, f"⚠️ Ошибка генерации временной ссылки!", 120, parse_mode="HTML")
			logger.error(f"Ошибки вызова get_temp_link(): {answer['details']}")
			return
		

def send_user_stat(user_id):
	paid_days = database_manager.get_paid_days(user_id)
	main_location_id = database_manager.get_user_server_id(user_id)
	backup_location_id = database_manager.get_user_server_id(user_id, main=False)
	if main_location_id is None:
		bot.send_message(user_id, f"❌ Не удалось загрузить основную локацию", reply_markup=status_keyboard())
	if backup_location_id is None:
		bot.send_message(user_id, f"❌ Не удалось загрузить резервную локацию", reply_markup=status_keyboard())

	
	country_conf_main = server_manager.get_country_by_server_id(main_location_id)
	country_conf_backup = server_manager.get_country_by_server_id(backup_location_id)
	if is_admin(user_id) or is_owner(user_id):
		bot.send_message(user_id, 
			f"""
				<b>🌍 Ваши локации:</b>\n
				Основная  локация: {country_conf_main.emoji} {country_conf_main.name}\n
				Резервная локация: {country_conf_backup.emoji} {country_conf_backup.name}\n
				Ваш ID: <code>{user_id}</code>""",
			reply_markup=status_keyboard(),
			parse_mode='HTML')
	else:
		if paid_days > 0:
			bot.send_message(user_id, 
				f"""<b>📆 У вас осталось: {paid_days} д.</b>\n
				Основная локация: {country_conf_main.emoji} {country_conf_main.name}\n
				Резервная локация: {country_conf_backup.emoji} {country_conf_backup.name}\n
				Ваш ID: <code>{user_id}</code>""",
				reply_markup=status_keyboard(),
				parse_mode='HTML')
		else:
			bot.send_message(user_id, 
				f"❌ У вас нет активной подписки\nВаш ID: <code>{user_id}</code>",
				reply_markup=cancel_keyboard(),
				parse_mode='HTML')


def send_statistic(message):
	user_id = message.from_user.id
	num_all_users = len(database_manager.get_all_user_ids())
	num_active_users = len(database_manager.get_active_user_ids())
	today = datetime.now(timezone.utc)
	month_sales = database_manager.get_month_sales(today.year, today.month)
	statistic_message = f"""
		<b>📊 Статистика пользователей</b>\n
		👥 Всего пользователей: <b>{num_all_users}</b>\n
		✅ С активной подпиской: <b>{num_active_users}</b>\n\n
		<b>💰 Продажи за текущий месяц</b>\n
		📅 Период: <b>{today.strftime("%m.%Y")}</b>\n
		💵 Выручка: <b>{month_sales} ₽</b>"""
		
	bot.send_message(user_id, 
		statistic_message,
		reply_markup=cancel_keyboard(),
		parse_mode='HTML')
		