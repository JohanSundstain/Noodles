import telebot
import random
import schedule
import time
import threading
import sqlite3
import logging
import sys
from telebot import types
from datetime import datetime, timedelta
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
	from config import TOKEN, ADMIN_ID, OWNER_ID, PRICES, RESONS, NUMBER, BONUS, DAYS, BOT_LINK
except ImportError as e:
	logger.error(f"Ошибка импорта config: {e}")
	logger.error("Создайте файл config.py со следующими переменными:")
	logger.error("TOKEN, ADMIN_ID, OWNER_ID, PRICES, RESONS, NUMBER")
	sys.exit(1)

try:
	from utils import create_user, delete_user_by_name, get_users_link, qrcode_generate
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
class Database:
	def __init__(self, db_path="bot.db"):
		self.db_path = db_path
		self.connection = None
		self._connect()
		self._init_tables()

	def _connect(self):
		"""Создание подключения с обработкой ошибок"""
		try:
			if self.connection:
				self.connection.close()
			self.connection = sqlite3.connect(
				self.db_path,
				check_same_thread=False,
				timeout=30  # Таймаут на случай блокировки
			)
			self.connection.row_factory = sqlite3.Row
			logger.info(f"Подключение к БД {self.db_path} установлено")
		except sqlite3.Error as e:
			logger.error(f"Ошибка подключения к БД: {e}")
			raise

	def _init_tables(self):
		"""Инициализация таблиц с проверкой"""
		try:
			with self.connection:
				self.connection.execute("""
					CREATE TABLE IF NOT EXISTS users (
						user_id INTEGER PRIMARY KEY,
						paid_days INTEGER DEFAULT 0)
				""")
			
				self.connection.execute("""
					CREATE TABLE IF NOT EXISTS referrals (
						user_id INTEGER PRIMARY KEY,
						inviter INTEGER,
						reward_given BOOLEAN DEFAULT FALSE
					)
				""")
				logger.info("Таблицы БД инициализированы")
		except sqlite3.Error as e:
			logger.error(f"Ошибка инициализации таблиц: {e}")
			raise

	@contextmanager
	def cursor(self):
		"""Контекстный менеджер для курсоров с автоматическим закрытием"""
		cursor = self.connection.cursor()
		try:
			yield cursor
		except sqlite3.Error as e:
			logger.error(f"Ошибка SQL: {e}")
			self.connection.rollback()
			raise
		finally:
			cursor.close()

	def execute(self, query, params=None):
		"""Выполнение запроса с автоматическим коммитом"""
		try:
			with self.cursor() as cur:
				if params:
					cur.execute(query, params)
				else:
					cur.execute(query)
				self.connection.commit()
				return cur
		except sqlite3.Error as e:
			logger.error(f"Ошибка выполнения запроса: {query}, params={params}, error={e}")
			self.connection.rollback()
			raise

	def fetch_one(self, query, params=None):
		"""Получение одной записи"""
		try:
			with self.cursor() as cur:
				if params:
					cur.execute(query, params)
				else:
					cur.execute(query)
				return cur.fetchone()
		except sqlite3.Error as e:
			logger.error(f"Ошибка fetch_one: {e}")
			return None

	def fetch_all(self, query, params=None):
		"""Получение всех записей"""
		try:
			with self.cursor() as cur:
				if params:
					cur.execute(query, params)
				else:
					cur.execute(query)
				return cur.fetchall()
		except sqlite3.Error as e:
			logger.error(f"Ошибка fetch_all: {e}")
			return []

	def close(self):
		"""Закрытие соединения"""
		if self.connection:
			self.connection.close()
			logger.info("Соединение с БД закрыто")

	
	def check_user(self, user_id):
		row = self.fetch_one("SELECT * FROM users WHERE user_id=?", (user_id,))
		return row is not None

	def create_new_user(self, user_id, ref=None):
		if self.check_user(user_id):
			return
		
		self.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
		
		if ref is not None and not self.check_user(ref):
			ref = None


		if ref is not None:
			self.execute("INSERT INTO referrals (user_id, inviter) VALUES (?, ?)", (user_id, ref))
		else:
			self.execute("INSERT INTO referrals (user_id) VALUES (?)", (user_id,))

	def create_subsription(self, user_id, days):
		if not self.check_user(user_id):
			return
		self.execute("UPDATE users SET paid_days=paid_days+? WHERE user_id=?", (days, user_id))
		
		row = self.fetch_one("SELECT inviter, reward_given FROM referrals WHERE user_id=?", (user_id,))
		if row is None:
			return
		
		inviter, reward_given = row
		# Если есть приглашающий и награда не получена 
		if (inviter is not None) and (reward_given == False) and (days > 1):
			bot.send_message(user_id, f"✅ Бонус {BONUS} дней за инвайт получен!")
			self.execute("UPDATE users SET paid_days=paid_days + ?  WHERE user_id=?", (BONUS, inviter))
			self.execute("UPDATE referrals SET reward_given=? WHERE user_id=?", (True, user_id))
		else:
			return
		
	def get_paid_days(self, user_id):
		if not self.check_user(user_id):
			return
		row = self.fetch_one("SELECT paid_days FROM users WHERE user_id=?", (user_id,))
		return row["paid_days"] if row else 0

	def reduce_days(self):
		all_users = self.fetch_all("SELECT user_id, paid_days FROM users")
		for user_id, paid_days in all_users:
			paid_days -= 1
			if paid_days <= 0:
				paid_days = 0
				bot.send_message(user_id, "⚠️ Ваша подписка истекла.\nЧтобы не видеть это сообщение заблокируйте и удалите бота")
				delete_user_by_name(user_id)
			else:
				self.execute("UPDATE users SET paid_days=?  WHERE user_id=?", (paid_days, user_id))

# Создание экземпляра БД
try:
	db = Database()
except Exception as e:
	logger.error(f"Критическая ошибка инициализации БД: {e}")
	sys.exit(1)

# временный выбор тарифа (с защитой от потери данных)
user_plan = {}

# -------------------------
# START MENU
# -------------------------
@bot.message_handler(commands=['start'])
def start(message):

	args = message.text.split()

	if len(args) > 1:
		referrer = args[1]
		if referrer == message.from_user.id:
			referrer = None
	else:
		referrer = None

	db.create_new_user(message.from_user.id, referrer)

	try:
		markup = types.InlineKeyboardMarkup()
		markup.add(types.InlineKeyboardButton("💳 Купить подписку", callback_data="buy"))
		markup.add(types.InlineKeyboardButton("📊 Мой статус", callback_data="status"))
		markup.add(types.InlineKeyboardButton("🔗 Реферальная ссылка", callback_data="ref"))
		markup.add(types.InlineKeyboardButton("🔍 Справка", callback_data="help"))
		
		bot.send_message(
			message.chat.id,
			"Добро пожаловать 👇",
			reply_markup=markup
		)
		logger.info(f"Пользователь {message.from_user.id} запустил бота")
	except Exception as e:
		logger.error(f"Ошибка в start: {e}")
		bot.send_message(message.chat.id, "⚠️ Произошла ошибка. Попробуйте позже.")

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

		markup = types.InlineKeyboardMarkup()
		markup.add(
			types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"approve:{user_id}:{plan}"),
			types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject:{user_id}:{plan}")
		)

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
				reply_markup=markup
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
				reply_markup=markup
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
				reply_markup=markup
			)

		# -------------------------
		# 📦 fallback
		# -------------------------
		else:
			bot.send_message(
				ADMIN_ID,
				caption + "\n\n❗ Неизвестный тип файла"
			)

		bot.send_message(user_id, "⏳ Файл получен, ожидайте проверки")

	except Exception as e:
		logger.error(f"Ошибка: {e}")
		bot.send_message(message.from_user.id, "⚠️ Ошибка обработки файла")

# -------------------------
# CALLBACKS
# -------------------------
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
	try:
		data = call.data
		# -------------------------
		# BUY MENU
		# -------------------------
		if data == "buy":
			markup = types.InlineKeyboardMarkup()
			markup.add(types.InlineKeyboardButton("1 месяц - 100₽", callback_data="plan:1"))
			markup.add(types.InlineKeyboardButton("3 месяца - 250₽", callback_data="plan:3"))
			markup.add(types.InlineKeyboardButton("6 месяцев - 450₽", callback_data="plan:6"))
			
			bot.send_message(call.message.chat.id, "Выберите тариф:", reply_markup=markup)
			bot.answer_callback_query(call.id)
			return
		
		# -------------------------
		# STATUS
		# -------------------------
		if data == "status":
			user_id = call.from_user.id
			
			days = db.get_paid_days(user_id)
			
			if days == 0:
				bot.send_message(user_id, "❌ У вас нет активной подписки")
				bot.answer_callback_query(call.id)
				return
			
			# Генерация ссылки
			try:
				vless_url = get_users_link(user_id)
				if vless_url:
					try:
						buffer = qrcode_generate(vless_url)
						bot.send_photo(user_id, buffer)
					except Exception as e:
						logger.error(f"Ошибка генерации QR-кода: {e}")
						
					bot.send_message(
						user_id,
						f"```\n{vless_url}\n```",
						parse_mode="Markdown"
					)
				else:
					logger.error(f"Не удалось найти ссылку {user_id}")
					bot.send_message(user_id, "⚠️ Не удалось найти ссылку. Обратитесь в поддержку.")

			except Exception as e:
				logger.error(f"Ошибка создания пользователя {user_id}: {e}")
				bot.send_message(user_id, "⚠️ Не удалось найти ссылку. Обратитесь в поддержку.")
				
			bot.send_message(user_id, f"✅ Дней до конца подписки: {(days)}")
			
			bot.answer_callback_query(call.id)
			return
		
		# -------------------------
		# REF
		# -------------------------
		if data == "ref":
			link = f"{BOT_LINK}?start={call.from_user.id}"
			bot.send_message(call.message.chat.id, f"Ваша реферальная ссылка: {link}")
			return

		# -------------------------
		# HELP
		# -------------------------
		if data == "help":
			message = "После покупки вы получаете ссылку и qrcode для подключения к прокси серверу.\n" \
			"Ссылку необходимо вставить в клиент приложения v2ray.\n" \
			"Android: 	v2rayTun\n "\
			"IOS: 		v2ray\n"\
			"Windows:	https://github.com/2dust/v2rayNG/releases\n" \
			"Дополнительные вопросы можно писать сюда -> @Johan_Sundstain"
			bot.send_message(call.message.chat.id, message)
			return


		# -------------------------
		# CHOOSE PLAN
		# -------------------------
		if data.startswith("plan:"):
			plan = int(data.split(":")[1])
			user_plan[call.from_user.id] = plan
			
			bot.send_message(
				call.message.chat.id,
				f"Вы выбрали {plan} мес."
			)
			
			# Безопасное получение случайной причины
			try:
				random_reason = random.choice(RESONS) if RESONS else "Оплата подписки"
			except (IndexError, TypeError):
				random_reason = "Оплата подписки"
			
			bot.send_message(
				call.message.chat.id,
				f"Перевод по номеру телефона: +{NUMBER}\nСбер/ТБанк\nВ сообщении к переводу обязательно написать:"
			)
			bot.send_message(
				call.message.chat.id,
				f"```\n{random_reason}\n```",
				parse_mode="Markdown"
			)
			bot.send_message(
				call.message.chat.id,
				"В чат отправь скриншот операции. По вопросам пиши в личку @Johan_Sundstain"
			)
			
			bot.answer_callback_query(call.id)
			return
		
		# -------------------------
		# APPROVE
		# -------------------------
		if data.startswith("approve:"):
			user_id = int(data.split(":")[1])
			plan = int(data.split(":")[2])
								
			db.create_subscription(user_id, DAYS[plan])
			
			# Генерация ссылки
			try:
				vless_url = create_user(user_id)
				
				if vless_url:
					# Генерация QR-кода
					try:
						buffer = qrcode_generate(vless_url)
						bot.send_photo(user_id, buffer)
					except Exception as e:
						logger.error(f"Ошибка генерации QR-кода: {e}")
					
					bot.send_message(
						user_id,
						f"```\n{vless_url}\n```",
						parse_mode="Markdown"
					)
				else:
					logger.error(f"Не удалось создать ссылку для пользователя {user_id}")
					bot.send_message(user_id, "⚠️ Ошибка генерации ссылки. Обратитесь в поддержку.")
					
			except Exception as e:
				logger.error(f"Ошибка создания пользователя {user_id}: {e}")
				bot.send_message(user_id, "⚠️ Ошибка при создании подключения. Обратитесь в поддержку.")
			
			bot.send_message(
				user_id,
				f"✅ Вы купили {DAYS[plan]} дней подписки"
			)
			
			try:
				bot.edit_message_caption(
					chat_id=ADMIN_ID,
					message_id=call.message.message_id,
					caption="✅ ПОДТВЕРЖДЕНО"
				)
			except Exception as e:
				logger.warning(f"Не удалось отредактировать сообщение администратора: {e}")
			
			bot.send_message(OWNER_ID, f"✅ Куплена подписка на сумму {PRICES.get(int(plan), 'неизвестно')} ₽")
			
			bot.answer_callback_query(call.id, "✅ Подписка подтверждена")
			return
		
		# -------------------------
		# REJECT
		# -------------------------
		if data.startswith("reject:"):
			user_id = int(data.split(":")[1])
			plan = int(data.split(":")[2])			
			try:
				bot.send_message(
					user_id,
					"❌ Оплата отклонена. Попробуйте ещё раз или свяжитесь с поддержкой."
				)
			except Exception as e:
				logger.warning(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
			
			try:
				bot.edit_message_caption(
					chat_id=ADMIN_ID,
					message_id=call.message.message_id,
					caption="❌ ОТКЛОНЕНО"
				)
			except Exception as e:
				logger.warning(f"Не удалось отредактировать сообщение администратора: {e}")
			
			bot.answer_callback_query(call.id, "❌ Платёж отклонён")
			return
		
	except Exception as e:
		logger.error(f"Ошибка в callback: {e}")
		try:
			bot.answer_callback_query(call.id, "⚠️ Произошла ошибка", show_alert=True)
		except:
			pass

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