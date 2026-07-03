from telebot import types

from config import (
	BUY_BUTTON,
	TEMP_LINK_BUTTON,
	AMDINS_LINK_BUTTON,
	STATISTIC_BUTTON,
	REF_BUTTON,
	STATUS_BUTTON,
	HELP_BUTTON)


def admin_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        is_persistent=True
    )
    markup.row(types.KeyboardButton(AMDINS_LINK_BUTTON), types.KeyboardButton(TEMP_LINK_BUTTON))
    markup.row(types.KeyboardButton(STATISTIC_BUTTON))
    markup.row(types.KeyboardButton(HELP_BUTTON))
    return markup


def user_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        is_persistent=True
    )
    markup.row(types.KeyboardButton(BUY_BUTTON), types.KeyboardButton(STATUS_BUTTON))
    markup.row(types.KeyboardButton(REF_BUTTON))
    markup.row(types.KeyboardButton(HELP_BUTTON))
    return markup

def owner_meny_keyboard():

	pass

def cancel_keyboard():
	markup = types.InlineKeyboardMarkup()
	markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
	return markup
	
def buy_keyboard():
	markup = types.InlineKeyboardMarkup()
	markup.add(types.InlineKeyboardButton("1 месяц - 100₽", callback_data="plan:1"))
	markup.add(types.InlineKeyboardButton("3 месяца - 250₽", callback_data="plan:3"))
	markup.add(types.InlineKeyboardButton("6 месяцев - 450₽", callback_data="plan:6"))
	markup.add(types.InlineKeyboardButton("Ввести код", callback_data="plan:-1"))
	markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
	return markup

def temp_link_keyboard():
	markup = types.InlineKeyboardMarkup()
	markup.add(types.InlineKeyboardButton("1 месяц", callback_data="temp:1"))
	markup.add(types.InlineKeyboardButton("3 месяца", callback_data="temp:3"))
	markup.add(types.InlineKeyboardButton("6 месяцев", callback_data="temp:6"))
	markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
	return markup

def status_keyboard():
	markup = types.InlineKeyboardMarkup()
	markup.add(types.InlineKeyboardButton("🔗 Ссылка", callback_data="link"))
	markup.add(types.InlineKeyboardButton("🔳 QR", callback_data="qr"))
	markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
	return markup

def admin_approve_reject_keyboard(user_id, plan):
	markup = types.InlineKeyboardMarkup()
	markup.add(types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"approve:{user_id}:{plan}"))
	markup.add(types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject:{user_id}:{plan}"))

	return markup

