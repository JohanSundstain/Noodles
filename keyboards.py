from telebot import types

def admin_menu_keyboard():
	markup = types.InlineKeyboardMarkup()
	markup.add(types.InlineKeyboardButton("🔗 Временная ссылка", callback_data="temp_link"))
	markup.add(types.InlineKeyboardButton("💳 Купить подписку", callback_data="buy"))
	markup.add(types.InlineKeyboardButton("📊 Cтатус", callback_data="status"))
	markup.add(types.InlineKeyboardButton("🔍 Справка", callback_data="help"))
	return markup

def user_menu_keyboard():
	markup = types.InlineKeyboardMarkup()
	markup.add(types.InlineKeyboardButton("💳 Купить подписку", callback_data="buy"))
	markup.add(types.InlineKeyboardButton("📊 Cтатус", callback_data="status"))
	markup.add(types.InlineKeyboardButton("🔗 Реферальная ссылка", callback_data="ref"))
	markup.add(types.InlineKeyboardButton("🔍 Справка", callback_data="help"))
	return markup

def buy_keyboard():
	markup = types.InlineKeyboardMarkup()
	markup.add(types.InlineKeyboardButton("1 месяц - 100₽", callback_data="plan:1"))
	markup.add(types.InlineKeyboardButton("3 месяца - 250₽", callback_data="plan:3"))
	markup.add(types.InlineKeyboardButton("6 месяцев - 450₽", callback_data="plan:6"))
	markup.add(types.InlineKeyboardButton("Ввести код", callback_data="plan:-1"))
	return markup

def temp_link_keyboard():
	markup = types.InlineKeyboardMarkup()
	markup.add(types.InlineKeyboardButton("1 месяц", callback_data="temp:1"))
	markup.add(types.InlineKeyboardButton("3 месяца", callback_data="temp:3"))
	markup.add(types.InlineKeyboardButton("6 месяцев", callback_data="temp:6"))

	return markup

def add_return_keyboard(markup=None):
	if markup is None:
		markup = types.InlineKeyboardMarkup()
	markup.add(types.InlineKeyboardButton("Меню", callback_data="menu"))
	return markup

def status_keyboard():
	markup = types.InlineKeyboardMarkup()
	markup.add(types.InlineKeyboardButton("🔗 Ссылка", callback_data="link"))
	markup.add(types.InlineKeyboardButton("🔳 QR", callback_data="qr"))

	return markup

def admin_approve_reject_keyboard(user_id, plan):
	markup = types.InlineKeyboardMarkup()
	markup.add(types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"approve:{user_id}:{plan}"))
	markup.add(types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject:{user_id}:{plan}"))

	return markup

