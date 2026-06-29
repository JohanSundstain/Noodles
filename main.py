import telebot
import random
import schedule
import time
import threading
import sqlite3
import logging
import sys
from telebot import types
from contextlib import contextmanager

# Настройка логирования
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
	handlers=[
		logging.FileHandler('bot.log'),
		logging.StreamHandler(sys.stdout)
	]
)
logger = logging.getLogger(__name__)

try:
	from config import TOKEN, ADMIN_ID, OWNER_ID, PRICES, NUMBER, BONUS, DAYS, BOT_LINK
except ImportError as e:
	logger.error(f"Ошибка импорта config: {e}")
	logger.error("Создайте файл config.py со следующими переменными:")
	logger.error("TOKEN, ADMIN_ID, OWNER_ID, PRICES, RESONS, NUMBER")
	sys.exit(1)

try:
	from database import Database
except ImportError as e:
	logger.error(f"Ошибка импорта database: {e}")
	sys.exit(1)

try:
	from utils import create_user, delete_users_link, get_users_link, qrcode_generate, check_user, generate_secure_code
except ImportError as e:
	logger.error(f"Ошибка импорта utils: {e}")
	logger.error("Убедитесь, что файл utils.py существует и содержит функции create_user и delete_user_by_name")
	sys.exit(1)

# Инициализация бота с обработкой ошибок
try:
	bot = telebot.TeleBot(TOKEN)
	bot.get_me()  # Проверка токена
	logger.info("Бот успешно инициализирован")
except Exception as e:
	logger.error(f"Ошибка инициализации бота: {e}")
	sys.exit(1)

# -------------------------
# SQLITE INIT С ОТКАЗОУСТОЙЧИВОСТЬЮ
# -------------------------

# Создание экземпляра БД
try:
	db = Database()
except Exception as e:
	logger.error(f"Критическая ошибка инициализации БД: {e}")
	sys.exit(1)

# временный выбор тарифа (с защитой от потери данных)
user_plan = {}
# хранение временных ссылок в формате {юзер:(код, план)}
temp_links = {}

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


def show_menu(call):
	user_id = call.from_user.id

	if user_id == ADMIN_ID:
		keyboard = admin_menu_keyboard()
	else:
		keyboard = user_menu_keyboard()

	bot.edit_message_text("Меню", user_id, call.message.message_id, reply_markup=keyboard)

	bot.answer_callback_query(call.id)

def show_temp_link_keyboard(call):
	keyboard = add_return_keyboard(temp_link_keyboard())

	bot.edit_message_text("Временная ссылка", ADMIN_ID, call.message.message_id, reply_markup=keyboard)

	bot.answer_callback_query(call.id)

def show_buy(call):
	user_id = call.from_user.id

	keyboard = add_return_keyboard(buy_keyboard())

	bot.edit_message_text("Купить подписку", user_id, call.message.message_id, reply_markup=keyboard)

	bot.answer_callback_query(call.id)

def show_status(call):
	user_id = call.from_user.id

	message = ""

	days = db.get_paid_days(user_id)
	if days == 0:
		message = "❌ У вас нет активной подписки.\n"
		bot.edit_message_text(message, user_id, call.message.message_id, reply_markup=add_return_keyboard())
		bot.answer_callback_query(call.id)
	else:
		message = f"✅ Дней до конца подписки: {days}.\n"
		keyboard = add_return_keyboard(status_keyboard())
		bot.edit_message_text(message, user_id, call.message.message_id, reply_markup=keyboard)
		bot.answer_callback_query(call.id)

def show_ref(call):
	user_id = call.from_user.id
	
	link = f"{BOT_LINK}?start={call.from_user.id}"
	bot.edit_message_text(f"Ваша реферальная ссылка: <code>{link}</code>", user_id, call.message.message_id, reply_markup=add_return_keyboard(), parse_mode="HTML")

	bot.answer_callback_query(call.id)

def show_help(call):
	user_id = call.from_user.id
	
	message = """
	<b>📖 Инструкция по подключению</b>

	После покупки вы получите:
	• 🔗 персональную ссылку
	• 📱 QR-код для быстрого подключения

	<b>Как подключиться?</b>

	1️⃣ Установите клиент <b>V2Ray</b> на своё устройство.

	<b>📱 Android</b>
	<code>v2rayTun</code>

	<b>🍏 iPhone (iOS)</b>
	<code>v2ray</code>

	<b>🖥 Windows</b>
	https://github.com/2dust/v2rayNG/releases

	2️⃣ Откройте приложение.

	3️⃣ Импортируйте полученную ссылку или отсканируйте QR-код.

	<b>❓ Возникли вопросы?</b>

	Напишите:
	<b>@Johan_Sundstain</b>
	"""
	
	bot.edit_message_text(message, user_id, call.message.message_id, reply_markup=add_return_keyboard(), parse_mode="HTML")

	bot.answer_callback_query(call.id)

def show_plan(call):
	user_id = call.from_user.id
	data = call.data

	plan = int(data.split(":")[1])
	user_plan[call.from_user.id] = plan

	if plan == -1:
		message = "<b>Отправьте боту код в чат командой:</b>\n<code>/code КОД</code>\n"
		bot.edit_message_text(message, user_id, call.message.message_id, reply_markup=add_return_keyboard(), parse_mode="HTML")
	else:
		message = (
			f"<b>Вы выбрали:</b> {plan} мес.\n\n"
			f"<b>Оплата по номеру телефона:</b>\n"
			f"<code>+{NUMBER}</code>\n"
			f"<b>Банки:</b> Сбер / ТБанк\n\n"
			f"После оплаты отправьте <b>результат операции</b> "
			f"(файл или скриншот) в чат бота."
		)
		bot.edit_message_text(message, user_id, call.message.message_id, reply_markup=add_return_keyboard(), parse_mode="HTML")
		
	bot.answer_callback_query(call.id)

def show_approved(call):
	data = call.data
	user_id = int(data.split(":")[1])
	plan = int(data.split(":")[2])
	# обновляет ли пользователь подписку
	is_update = True if db.get_paid_days(user_id) > 0 else False
	db.create_subscription(user_id, DAYS[plan])

	if is_update:
		message = "✅ Подписка продлена."
		send_temp_message(bot, user_id, message, 30)
	else:
		# Генерация ссылки
		try:
			vless_url = create_user(user_id)
			send_qr_and_link(user_id, vless_url)
		except Exception as e:
			logger.error(f"Ошибка создания пользователя {user_id}: {e}")	
			send_temp_message(bot, user_id, f"✅ Вы купили {DAYS[plan]} дней подписки", 30)
		try:
			bot.edit_message_caption(
				chat_id=ADMIN_ID,
				message_id=call.message.message_id,
				caption="✅ ПОДТВЕРЖДЕНО"
			)
		except Exception as e:
			logger.warning(f"Не удалось отредактировать сообщение администратора: {e}")
			
	bot.send_message(OWNER_ID, f"✅ Куплена подписка на сумму {PRICES.get(int(plan), 'неизвестно')} ₽")
			
	message = "Сообщение исчезнет через 30 сек.\nПовторно получить ссылку: <code>Меню</code> -> <code>Статус</code>"
	send_temp_message(bot, user_id, message, 30, parse_mode="HTML")

	bot.answer_callback_query(call.id)

	return

def show_reject(call):
	data = call.data
	user_id = int(data.split(":")[1])
	plan = int(data.split(":")[2])			
	try:
		send_temp_message(bot, user_id,"❌ Оплата отклонена. Попробуйте ещё раз или свяжитесь с поддержкой.", 30)
	except Exception as e:
		logger.warning(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
			
	try:
		bot.edit_message_caption(chat_id=ADMIN_ID,message_id=call.message.message_id,caption="❌ ОТКЛОНЕНО")
	except Exception as e:
		logger.warning(f"Не удалось отредактировать сообщение администратора: {e}")
	bot.answer_callback_query(call.id)

def show_temp_link(call):
	data = call.data
	plan = int(data.split(":")[1])
	code = generate_secure_code(5)
	user_id = int(generate_secure_code(7))
	temp_links[code] = (user_id, plan)
	vless_url = create_user(user_id)

	send_qr_and_link(user_id, vless_url)
	temp_link_deleter(bot, user_id, 60) # не забыть поменять на час
	bot.answer_callback_query(call.id)

def send_qr_and_link(user_id, url):
	if url:
	# Генерация QR-кода
		try:
			buffer = qrcode_generate(url)
			send_temp_photo(bot, user_id, buffer, 120)
			send_temp_message(bot, user_id, f"<code>{url}</code>", 120, parse_mode="HTML")
		except Exception as e:
			logger.error(f"Ошибка генерации QR-кода: {e}")			
	else:
		logger.error(f"Не удалось создать ссылку для пользователя {user_id}")
		send_temp_message(bot, user_id, "⚠️ Ошибка генерации ссылки. Обратитесь в поддержку.", 30)

# -------------------------
# START MENU
# -------------------------
@bot.message_handler(commands=['start'])
def start(message):
	args = message.text.split()
	user_id = message.from_user.id

	if len(args) > 1:
		referrer = int(args[1])
		if referrer == message.from_user.id:
			referrer = None
	else:
		referrer = None

	db.create_new_user(message.from_user.id, referrer)

	try:
		if user_id == ADMIN_ID:
			keyboard = admin_menu_keyboard()
		else:
			keyboard = user_menu_keyboard()

		bot.send_message(user_id, "Меню", reply_markup=keyboard) 

	except Exception as e:
		logger.error(f"Ошибка в start: {e}")
		bot.send_message(user_id, "⚠️ Произошла ошибка. Попробуйте позже.")

# -------------------------
# PHOTO (скрин оплаты)
# -------------------------
@bot.message_handler(content_types=['photo', 'document', 'video'])
def handle_any(message):
	try:
		user_id = message.from_user.id
		username = message.from_user.username or "no_username"
		plan = user_plan.get(user_id)

		if not plan:
			bot.send_message(user_id, "❗ Сначала выбери тариф")
			return

		keyboard = admin_approve_reject_keyboard(user_id, plan)

		caption = f"🆕 Оплата\nUser: @{username}\nТариф: {plan} мес\nID: {user_id}"

		# -------------------------
		# 📸 PHOTO
		# -------------------------
		if message.content_type == 'photo':
			file_id = message.photo[-1].file_id

			bot.send_photo(
				ADMIN_ID,
				file_id,
				caption=caption,
				reply_markup=keyboard
			)

		# -------------------------
		# 📎 DOCUMENT (pdf, zip, txt и т.д.)
		# -------------------------
		elif message.content_type == 'document':

			file_id = message.document.file_id

			bot.send_document(
				ADMIN_ID,
				file_id,
				caption=caption,
				reply_markup=keyboard
			)

		# -------------------------
		# 🎥 VIDEO
		# -------------------------
		elif message.content_type == 'video':

			file_id = message.video.file_id

			bot.send_video(
				ADMIN_ID,
				file_id,
				caption=caption,
				reply_markup=keyboard
			)

		# -------------------------
		# 📦 fallback
		# -------------------------
		else:
			bot.send_message(
				ADMIN_ID,
				caption + "\n\n❗ Неизвестный тип файла"
			)

		  # УДАЛЯЕМ сообщение пользователя
		try:
			bot.delete_message(user_id, message.message_id)
			logger.info(f"Сообщение пользователя {user_id} удалено")
		except Exception as e:
			logger.warning(f"Не удалось удалить сообщение пользователя: {e}")	

		send_temp_message(bot, user_id,"⏳ Файл получен, ожидайте проверки", 30)
		### show_menu()

	except Exception as e:
		logger.error(f"Ошибка: {e}")
		bot.send_message(message.from_user.id, "⚠️ Ошибка обработки файла")

# -------------------------
# CODE (скрин оплаты)
# -------------------------
@bot.message_handler(content_types=['code'])
def handle_any(message):
	try:
		parts = message.text.split()
		user_id = message.from_user.id

		if len(parts) < 2:
			warning =  "❌ Вы не ввели код!\n" \
						   "<br>📝 Использование</br>: <code>/code КОД</code>\n" \
				            "<br>Пример</br>: <code>/code A7K2P</code>"
	
			send_temp_message(bot, user_id, warning, 30, parse_mode="HTML")
			
			return
		else:
			code = parts[1]
			# Если код верен
			if code in temp_links:
				temp_id, plan = temp_links[code]
				delete_users_link(temp_id)
				db.create_subscription(user_id, DAYS[plan])

				text = "✅ Код активиран."
				send_temp_message(bot, user_id, text, 30)
				vless_url = create_user(user_id)
				send_qr_and_link(user_id, vless_url)
			else:
				warning =  "❌ Неверный код!"
				send_temp_message(bot, user_id, warning, 30)
			try:
				bot.delete_message(user_id, message.message_id)
				logger.info(f"Сообщение пользователя {user_id} удалено")
			except Exception as e:
				logger.warning(f"Не удалось удалить сообщение пользователя: {e}")		

	except Exception as e:
		logger.error(f"Ошибка: {e}")
		bot.send_message(message.from_user.id, "⚠️ Ошибка обработки кода")

# -------------------------
# CALLBACKS
# -------------------------
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
	try:
		data = call.data
		# MENU
		if data == "menu":
			show_menu(call)
			return
		
		# BUY MENU
		if data == "buy":
			show_buy(call)
			return
		
		# STATUS
		if data == "status":
			show_status(call)
			return
	
		# REF
		if data == "ref":
			show_ref(call)
			return

		# HELP
		if data == "help":
			show_help(call)
			return

		# CHOOSE PLAN
		if data.startswith("plan:"):
			show_plan(call)
			return
		
		# CHOOSE PLAN FOR TEMP LINK
		if data == "temp_link":
			show_temp_link_keyboard(call)
			return
		
		# TEMP LINK FOR ADMIN
		if data.startswith("temp:"):
			show_temp_link(call)
			return

		# APPROVE
		if data.startswith("approve:"):
			show_approved(call)
			return
			
		# REJECT
		if data.startswith("reject:"):
			show_reject(call)
			return
			
		# QR
		if data == "qr":
			user_id = call.from_user.id
			vless_url = get_users_link(user_id)
			buffer = qrcode_generate(vless_url)
			send_temp_photo(bot, user_id, buffer, 30, caption="Сообщение исчезнет через 30 сек.")
			bot.answer_callback_query(call.id)
			return

		# LINK
		if data == "link":
			user_id = call.from_user.id
			vless_url = get_users_link(user_id)
			message = f"<code>{vless_url}</code>"
			send_temp_message(bot, user_id, message, 30, parse_mode="HTML")
			send_temp_message(bot, user_id, "Сообщение исчезнет через 30 сек.", 30, parse_mode="HTML")
			bot.answer_callback_query(call.id)
			return

	except Exception as e:
		logger.error(f"Ошибка в callback: {e}")

def send_temp_message(bot, chat_id, text, seconds=30, **kwargs):
	try:
		msg = bot.send_message(chat_id, text, **kwargs)

		def delete():
			try:
				bot.delete_message(chat_id, msg.message_id)
			except Exception as e:
				logger.error(f"Ошибка удаления сообщения: {e}")

		threading.Timer(seconds, delete).start()
	except Exception as e:
		logger.error(f"Ошибка при отправке временного сообщения: {e}")

def send_temp_photo(bot, chat_id, buffer, seconds=30, **kwargs):
	try:
		msg = bot.send_photo(chat_id, buffer, **kwargs)

		def delete():
			try:
				bot.delete_message(chat_id, msg.message_id)
			except Exception as e:
				logger.error(f"Ошибка удаления сообщения: {e}")

		threading.Timer(seconds, delete).start()
	except Exception as e:
		logger.error(f"Ошибка при отправке временного изображения: {e}")

def temp_link_deleter(temp_id, seconds=3600):
	try:
		def delete():
			try:
				delete_users_link(temp_id)
			except Exception as e:
				logger.error(f"Ошибка удаления сообщения: {e}")

		threading.Timer(seconds, delete).start()
	except Exception as e:
		logger.error(f"Ошибка при удалении временной ссылки: {e}")

def run_schedule():
	while True:
		schedule.run_pending()
		time.sleep(60)

def daily_job():
	db.reduce_days()

# -------------------------
# RUN С ОТКАЗОУСТОЙЧИВОСТЬЮ
# -------------------------
if __name__ == "__main__":

	try:
		logger.info("Запуск бота...")
		
		# Запуск фонового процесса
		# запуск раз в день
		schedule.every().day.at("00:00").do(daily_job)
		threading.Thread(target=run_schedule, daemon=True).start()
		logger.info("Фоновый процесс запущен")
		
		# Запуск бота с обработкой ошибок
		while True:
			try:
				bot.infinity_polling(timeout=60, long_polling_timeout=60)
			except Exception as e:
				logger.error(f"Ошибка в polling: {e}")
				logger.info("Перезапуск через 5 секунд...")
				time.sleep(5)
				continue
			break
			
	except KeyboardInterrupt:
		logger.info("Бот остановлен пользователем")
	except Exception as e:
		logger.error(f"Критическая ошибка: {e}")
	finally:
		db.close()
		logger.info("Ресурсы освобождены")