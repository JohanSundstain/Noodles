from servers import server_manager
from database import database_manager
from telebot.apihelper import ApiTelegramException
import time

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
	status_keyboard
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


def switch_country_task(call):
	send_temp_message(bot, call.from_user.id, "✈️ Изменение локации...")
	user_id = call.from_user.id
	data = call.data
	country = data.split(":")[1]

	if is_admin(user_id) or is_owner(user_id):
		country_ids = server_manager.get_country_ids(country) # получаем все серверы данной страны
		servers_load = database_manager.get_servers_load(country_ids) # получам загрузку каждого сервера

		new_server_id = min(servers_load, key=servers_load.get) # сервер с минимальным кол-вом юзером
		country_conf = server_manager.get_country_by_server_id(new_server_id) # получаем конфиг страны с серверами

		database_manager.update_user_server(user_id, new_server_id) # обновляем страну в базе
		message = f"""✅ Локация изменена: {country_conf.emoji} {country_conf.name}\n
			Получить обновленную ссылку: <code>Статус</code>"""
		bot.edit_message_text(message,
					call.message.chat.id, 
					call.message.message_id,
					reply_markup=cancel_keyboard(),
					parse_mode="HTML")
		return
	
	paid_days = database_manager.get_paid_days(user_id)

	message = f"""✅ Локация изменена: {country_conf.emoji} {country_conf.name}\n
			Старая ссылка (если была) будет удалена через 10 мин.\n
			Получить обновленную ссылку: <code>Статус</code>"""
	if paid_days > 0:

		country_ids = server_manager.get_country_ids(country) # получаем все серверы данной страны
		servers_load = database_manager.get_servers_load(country_ids) # получам загрузку каждого сервера

		new_server_id = min(servers_load, key=servers_load.get) # сервер с минимальным кол-вом юзером
		country_conf = server_manager.get_country_by_server_id(new_server_id) # получаем конфиг страны с серверами
		
		prev_server_id = database_manager.get_user_server_id(user_id) # id предыдущего сервера
		new_api_client = server_manager.get_api_server(new_server_id)  # новый апи клиент

		if (new_server_id == prev_server_id):
			message = f"""✅ Локация изменена: {country_conf.emoji} {country_conf.name}\n
			Старая ссылка (если была) будет удалена через 10 мин.\n
			Получить обновленную ссылку: <code>Статус</code>"""
			bot.edit_message_text(message,
					call.message.chat.id, 
					call.message.message_id,
					reply_markup=cancel_keyboard(),
					parse_mode="HTML")
			return

		if prev_server_id != 'none': # если ссылка уже была
			prev_api_client = server_manager.get_api_server(prev_server_id) # апи старого сервера
			prev_api_client.schedule_delete(user_id, 600) # через 10 минут удаляем старую ссылку
			
		database_manager.update_user_server(user_id, new_server_id) # обновляем страну в базе
		answer = new_api_client.create_user(user_id) # делаем запрос на сервер

		if answer['status'] == 'ok':
			bot.edit_message_text(message, call.message.chat.id,  call.message.message_id, reply_markup=cancel_keyboard(), parse_mode="Markdown")
		else:
			bot.edit_message_text(f" Ошибка создания пользователя.",
					call.message.chat.id, 
					call.message.message_id,
					reply_markup=cancel_keyboard(),
					parse_mode="Markdown")
	else:
		message = f"❌ Сначала оформите подписку."
		bot.edit_message_text(message,
					call.message.chat.id, 
					call.message.message_id,
					reply_markup=cancel_keyboard(),
					parse_mode="HTML")
		return

def get_and_send_link(call):
	send_temp_message(bot, call.from_user.id, "⏳ Генерация ссылки...")

	user_id = call.from_user.id

	user_server_id = database_manager.get_user_server_id(user_id) # получаем id сервера пользователя

	if user_server_id == 'none': # если не выбрана локация, то отказываем в генерации
		bot.delete_message(user_id, call.message.message_id)
		send_temp_message(bot, user_id, "❌ Не выбрана локация.", 30)
		return

	user_api_client = server_manager.get_api_server(user_server_id) # получаем апи клиент к серверу юзера
	answer = user_api_client.get_link(user_id)

	if answer["status"] == "ok":
		vless_url = answer["link"]
		buffer = qrcode_generate(vless_url)
		send_temp_photo(bot, user_id, buffer, 30, caption=f'<code>{vless_url}</code>', parse_mode='HTML')
	else:
		send_temp_message(bot, user_id, "❌ Проблемы с сервером, обратитесь в поддержку.", 30)
		logger.error(f"Ошибка получения ссылки от сервера {answer['details']}")


def create_subscription(user_id=None, plan=None, call=None):

	result = database_manager.create_subscription(user_id, DAYS[plan])

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
	send_temp_message(bot, ADMIN_ID, '⏳ Запрос обрабатывается...', 30)

	plan = call.data.split(":")[1]
	admin_server_id = database_manager.get_user_server_id(ADMIN_ID) # получаем id сервера админа

	if admin_server_id == 'none': # админ не выбрал локацию
		send_temp_message(bot, ADMIN_ID, "❌ Не выбрана локация.", 30)
		return 
	
	api_client = server_manager.get_api_server(admin_server_id) # получаем api клиента для сервера админа

	answer = api_client.get_temp_link(ADMIN_ID) # делаем запрос на сервер, чтобы создать временную ссылку
 
	if answer["status"] == "ok":
		vless_url = answer['link']
		code = generate_secure_code(6)
		temp_code_deleter(code, int(plan))
		buffer = qrcode_generate(vless_url)
		send_temp_photo(bot, ADMIN_ID, buffer, 120, caption=f'<code>{vless_url}</code>', parse_mode='HTML')
		send_temp_message(bot, ADMIN_ID, f"Код: <code>{code}</code>", 120, parse_mode="HTML")
	else:
		send_temp_message(bot, ADMIN_ID, f"⚠️ Ошибка генерации временной ссылки!", 120, parse_mode="HTML")
		logger.error(f"Ошибки вызова get_temp_link(): {answer['details']}")
		return
	
def send_user_stat(user_id):
	paid_days = database_manager.get_paid_days(user_id)
	location_id = database_manager.get_user_server_id(user_id)
	country_conf = server_manager.get_country_by_server_id(location_id)
	if is_admin(user_id) or is_owner(user_id):
		bot.send_message(user_id, f"Локация: {country_conf.emoji} {country_conf.name}", reply_markup=status_keyboard())
	else:
		if paid_days > 0:
			bot.send_message(user_id, 
				f"У вас осталось: {paid_days} д.\nЛокация: {country_conf.emoji} {country_conf.name}\nВаш ID: {user_id}",
				reply_markup=status_keyboard())
		else:
			bot.send_message(user_id, f"У вас нет активной подписки\nВаш ID: {user_id}", reply_markup=cancel_keyboard())
