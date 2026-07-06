from telebot import types

from config import (
	BUY_BUTTON,
	TEMP_LINK_BUTTON,
	STATISTIC_BUTTON,
	REF_BUTTON,
	STATUS_BUTTON,
	HELP_BUTTON,
	LOCATION_BUTTON)

from servers import server_manager

def cancel_keyboard():
	markup = types.InlineKeyboardMarkup()
	markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
	return markup


#######################
# ADMIN KEYBOARDS
######################

def admin_menu_keyboard():
	markup = types.ReplyKeyboardMarkup(
		resize_keyboard=True,
		is_persistent=True
	)
	markup.row(types.KeyboardButton(TEMP_LINK_BUTTON),types.KeyboardButton(LOCATION_BUTTON))
	markup.row(types.KeyboardButton(STATISTIC_BUTTON), types.KeyboardButton(STATISTIC_BUTTON))
	markup.row(types.KeyboardButton(HELP_BUTTON))
	return markup


def user_menu_keyboard():
	markup = types.ReplyKeyboardMarkup(
		resize_keyboard=True,
		is_persistent=True
	)
	markup.row(types.KeyboardButton(BUY_BUTTON),types.KeyboardButton(LOCATION_BUTTON))
	markup.row(types.KeyboardButton(REF_BUTTON),types.KeyboardButton(STATUS_BUTTON))
	markup.row(types.KeyboardButton(HELP_BUTTON))
	return markup

def owner_meny_keyboard():

	pass

#######################
# USER KEYBOARDS
######################


def country_keyboard():
	markup = types.InlineKeyboardMarkup()
	COUNTRIES = server_manager.get_contries()
	for country in COUNTRIES:
		if country != "UNKNOWN":
			markup.add(types.InlineKeyboardButton(f"{COUNTRIES[country].emoji} {COUNTRIES[country].name}", callback_data=f"country:{country}"))
	markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
	return markup
  
	
def buy_keyboard():
	markup = types.InlineKeyboardMarkup()
	markup.add(types.InlineKeyboardButton("1 месяц - 100₽", callback_data=f"plan:1"))
	markup.add(types.InlineKeyboardButton("3 месяца - 250₽", callback_data=f"plan:3"))
	markup.add(types.InlineKeyboardButton("6 месяцев - 450₽", callback_data=f"plan:6"))
	markup.add(types.InlineKeyboardButton("Ввести код", callback_data=f"plan:-1"))
	markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
	return markup

def temp_link_keyboard():
	markup = types.InlineKeyboardMarkup()
	markup.add(types.InlineKeyboardButton("1 месяц", callback_data=f"temp:1"))
	markup.add(types.InlineKeyboardButton("3 месяца", callback_data=f"temp:3"))
	markup.add(types.InlineKeyboardButton("6 месяцев", callback_data=f"temp:6"))
	markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
	return markup

def status_keyboard():
	markup = types.InlineKeyboardMarkup()
	markup.add(types.InlineKeyboardButton("🔗 Ссылка", callback_data="link"))
	markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
	return markup

def admin_approve_reject_keyboard(user_id, plan):
	markup = types.InlineKeyboardMarkup()
	markup.add(types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"approve:{user_id}:{plan}"))
	markup.add(types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject:{user_id}:{plan}"))

	return markup

