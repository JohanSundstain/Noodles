from telebot import types

from config import PLANS, BUTTONS
from servers import server_manager
from database import database_manager

def cancel_keyboard():
	markup = types.InlineKeyboardMarkup()
	markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
	return markup


#######################
# ADMIN KEYBOARDS
######################

def admin_menu_keyboard():
	markup = types.ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True)
	markup.row(types.KeyboardButton(BUTTONS['temp']), types.KeyboardButton(BUTTONS['location']))
	markup.row(types.KeyboardButton(BUTTONS['statistic']), types.KeyboardButton(BUTTONS['status']))
	markup.row(types.KeyboardButton(BUTTONS['help']))
	return markup


def user_menu_keyboard():
	markup = types.ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True)
	markup.row(types.KeyboardButton(BUTTONS['buy']),types.KeyboardButton(BUTTONS['location']))
	markup.row(types.KeyboardButton(BUTTONS['ref']),types.KeyboardButton(BUTTONS['status']))
	markup.row(types.KeyboardButton(BUTTONS['help']))
	return markup

#######################
# USER KEYBOARDS
######################

def country_keyboard(main_country=None):
	markup = types.InlineKeyboardMarkup()

	api_servers = server_manager.get_all_api()
	id_servers = server_manager.get_all_id()

	buttons = []

	for api_server in api_servers:
		if api_server.id == main_country:
			continue

		if api_server.id != "none":
			if main_country is None:
				result = database_manager.get_servers_load(id_servers)
				text = f"{str(api_server)} [{result.get(api_server.id, 0)}]"
				callback = f"country:{api_server.id}:main"
			else:
				result = database_manager.get_servers_load(id_servers, main=False)
				text = f"{str(api_server)} [{result.get(api_server.id, 0)}]"
				callback = f"country:{api_server.id}:backup"

			buttons.append(
				types.InlineKeyboardButton(
					text,
					callback_data=callback
				)
			)

	# добавляем по 2 кнопки в ряд
	for i in range(0, len(buttons), 2):
		markup.row(*buttons[i:i+2])

	markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="cancel"))

	return markup
	
def buy_keyboard():
	markup = types.InlineKeyboardMarkup()

	for index, plan in enumerate(PLANS):
		markup.add(types.InlineKeyboardButton(f"{plan['days']} дней - {plan['price']}₽", callback_data=f"plan:{index}"))

	markup.add(types.InlineKeyboardButton("Ввести код", callback_data=f"plan:-1"))
	markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
	return markup

def temp_link_keyboard():
	markup = types.InlineKeyboardMarkup()

	for index, plan in enumerate(PLANS):
		markup.add(types.InlineKeyboardButton(f"{plan['days']} д. - {plan['price']}₽", callback_data=f"temp:{index}"))
		
	markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
	return markup


def status_keyboard():
	markup = types.InlineKeyboardMarkup()
	markup.add(types.InlineKeyboardButton("🔗 Основная  ссылка", callback_data="link:main"))
	markup.add(types.InlineKeyboardButton("🔗 Резервная ссылка", callback_data="link:backup"))
	markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
	return markup


def admin_approve_reject_keyboard(user_id, plan):
	markup = types.InlineKeyboardMarkup()
	markup.add(types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"approve:{user_id}:{plan}"))
	markup.add(types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject:{user_id}:{plan}"))

	return markup

