import sqlite3
from contextlib import contextmanager
from pathlib import Path

from bot import bot
from config import BONUS
from logger import logger
from telegram_helpers import send_temp_message
from xray import delete_users_link

class Database:
	def __init__(self, db_path="bot.db"):
		base_dir = Path(__file__).resolve().parent
		db_file = Path(db_path)
		if not db_file.is_absolute():
			db_file = base_dir / db_file
		self.db_path = str(db_file)
		self._init_tables()

	def _connect(self):
		"""Создание нового подключения для каждой операции"""
		try:
			db_file = Path(self.db_path)
			db_file.parent.mkdir(parents=True, exist_ok=True)
			connection = sqlite3.connect(
				str(db_file),
				check_same_thread=False,
				timeout=30  # Таймаут на случай блокировки
			)
			connection.row_factory = sqlite3.Row
			logger.info(f"Подключение к БД {self.db_path} установлено")
			return connection
		except sqlite3.Error as e:
			logger.error(f"Ошибка подключения к БД: {e}")
			raise

	def _init_tables(self):
		"""Инициализация таблиц с проверкой"""
		try:
			with sqlite3.connect(self.db_path, check_same_thread=False, timeout=30) as connection:
				connection.row_factory = sqlite3.Row
				connection.execute("""
					CREATE TABLE IF NOT EXISTS users (
						user_id INTEGER PRIMARY KEY,
						paid_days INTEGER DEFAULT 0)
				""")
			
				connection.execute("""
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
		"""Контекстный менеджер для курсоров с отдельным соединением на каждую операцию"""
		connection = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
		connection.row_factory = sqlite3.Row
		cursor = connection.cursor()
		try:
			yield cursor
			connection.commit()
		except sqlite3.Error as e:
			logger.error(f"Ошибка SQL: {e}")
			connection.rollback()
			raise
		finally:
			cursor.close()
			connection.close()

	def execute(self, query, params=None):
		"""Выполнение запроса с автоматическим коммитом"""
		try:
			with self.cursor() as cur:
				if params:
					cur.execute(query, params)
				else:
					cur.execute(query)
				return cur
		except sqlite3.Error as e:
			logger.error(f"Ошибка выполнения запроса: {query}, params={params}, error={e}")
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
		"""Оставлено для совместимости, теперь соединения закрываются сразу после операции"""
		pass

	
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

	def create_subscription(self, user_id, days):
		if not self.check_user(user_id):
			return
		self.execute("UPDATE users SET paid_days=paid_days+? WHERE user_id=?", (days, user_id))
		
		row = self.fetch_one("SELECT inviter, reward_given FROM referrals WHERE user_id=?", (user_id,))
		if row is None:
			return
		
		inviter, reward_given = row
		# Если есть приглашающий и награда не получена 
		if (inviter is not None) and (reward_given == False) and (days > 1):
			try:
				send_temp_message(bot, inviter,f"✅ Бонус {BONUS} дней за инвайт получен!", 120)
				self.execute("UPDATE users SET paid_days=paid_days + ?  WHERE user_id=?", (BONUS, inviter))
				self.execute("UPDATE referrals SET reward_given=? WHERE user_id=?", (True, user_id))
			except Exception as e:
				logger.error(f"Ошибка при выдаче бонуса: {e}")
		else:
			return
		
	def get_paid_days(self, user_id):
		row = self.fetch_one("SELECT paid_days FROM users WHERE user_id=?", (user_id,))
		return row["paid_days"] if row else 0
	
	def reduce_days(self):
		all_users = self.fetch_all("SELECT user_id, paid_days FROM users")
		for row in all_users:  # Исправлено: row - это словарь
			user_id = row["user_id"]
			paid_days = row["paid_days"]
			paid_days -= 1
			if paid_days <= 0:
				paid_days = 0
				bot.send_message(user_id, "⚠️ Ваша подписка истекла.\nЧтобы не видеть это сообщение заблокируйте и удалите бота")
				logger.info(f"Юзер {user_id} кончились дни")
				self.execute("UPDATE users SET paid_days=?  WHERE user_id=?", (0, user_id))
				delete_users_link(user_id)
			else:
				logger.info(f"Юзер {user_id} уменьшено дней {paid_days}")
				self.execute("UPDATE users SET paid_days=?  WHERE user_id=?", (paid_days, user_id))
