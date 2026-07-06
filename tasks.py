from servers import server_manager
from database import database_manager

from utils import (
	qrcode_generate,
	send_temp_message,
	send_temp_photo,
	logger,
	generate_secure_code,
	temp_code_deleter,
	is_admin
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

def switch_country_task(call):
	user_id = call.from_user.id
	data = call.data
	country = data.split(":")[1]

	country_ids = server_manager.get_country_ids(country) # получаем все серверы данной страны
	servers_load = database_manager.get_servers_load(country_ids) # получам загрузку каждого сервера

	new_server_id = min(servers_load, key=servers_load.get) # сервер с минимальным кол-вом юзером
	country_conf = server_manager.get_country_by_server_id(new_server_id) # получаем конфиг страны с серверами
	
	prev_server_id = database_manager.get_user_server_id(user_id) # id предыдущего сервера
	new_api_client = server_manager.get_api_server(new_server_id)  # новый апи клиент

	if (new_server_id == prev_server_id):
		bot.edit_message_text(f"✅ Локация изменена: {country_conf.emoji} {country_conf.name}",
				call.message.chat.id, 
				call.message.message_id,
				reply_markup=cancel_keyboard(),
				parse_mode="Markdown")
		return

	if prev_server_id != 'none': # если ссылка уже была
		prev_api_client = server_manager.get_api_server(prev_server_id) # апи старого сервера
		prev_api_client.schedule_delete(user_id, 600) # через 10 минут удаляем старую ссылку
		
	database_manager.update_user_server(user_id, new_server_id) # обновляем страну в базе
	answer = new_api_client.create_user(user_id) # делаем запрос на сервер

	if answer['status'] == 'ok':
		bot.edit_message_text(f"✅ Локация изменена: {country_conf.emoji} {country_conf.name}",
				call.message.chat.id, 
				call.message.message_id,
				reply_markup=cancel_keyboard(),
				parse_mode="Markdown")
	else:
		bot.edit_message_text(f"❌ Ошибка создания пользователя.",
				call.message.chat.id, 
				call.message.message_id,
				reply_markup=cancel_keyboard(),
				parse_mode="Markdown")
		

def get_and_send_link(call):
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
		logger.error(f"Ошибка получения qrcode от сервера {answer['details']}")


def create_subscription(user_id, plan):
	send_temp_message(bot, user_id, f'СОЗДАЮ ПОДПИСКУ', 120)
	result = database_manager.create_subscription(user_id, DAYS[plan])

	send_temp_message(bot, user_id, f'✅ Вы купили {DAYS[plan]} дней подписки', 120)

	if result is not None:
		inviter_id = result['inviter_id']
		bot.send_message(inviter_id, f'✅ Бонус {BONUS} д. получен!')

	bot.send_message(OWNER_ID, f'✅ Куплена подписка на сумму {PRICES.get(plan, "неизвестно")} ₽')
	info_message = """Сообщение исчезнет через 120 сек.\n
	Получить ссылку: <code>Меню</code> -> <code>Статус</code>\n
	❗️ Обязательно выберите локацию, если купили подписку впервые.\n"""

	send_temp_message(bot, user_id, info_message, 120, parse_mode='HTML')


def create_temp_link(call):
	plan = call.data.split(":")[1]
	admin_server_id = database_manager.get_user_server_id(ADMIN_ID) # получаем id сервера админа

	if admin_server_id == 'none': # админ не выбрал локацию
		send_temp_message(bot, ADMIN_ID, "❌ Не выбрана локация.", 30)
		return 
	
	api_client = server_manager.get_api_server(admin_server_id) # получаем api клиента для сервера админа

	# TODO ИЗМЕНИТЬ ВРЕМЯ
	answer = api_client.get_temp_link(ADMIN_ID, 300) # делаем запрос на сервер, чтобы создать временную ссылку
 
	if answer["status"] == "ok":
		vless_url = answer['link']
		code = generate_secure_code(6)
		# TODO ИЗМЕНИТЬ ВРЕМЯ
		temp_code_deleter(code, int(plan), 300)
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
	if not is_admin(user_id):
		if paid_days > 0:
			bot.send_message(user_id, f"У вас осталось: {paid_days} д.\nЛокация: {country_conf.emoji} {country_conf.name}", reply_markup=status_keyboard())
		else:
			bot.send_message(user_id, "У вас нет активной подписки", reply_markup=cancel_keyboard())
	else:
		bot.send_message(user_id, f"Локация: {country_conf.emoji} {country_conf.name}", reply_markup=status_keyboard())