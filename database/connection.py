from contextlib import contextmanager
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL  # Например: 'sqlite:///bot.db'
from logger import logger
from .models import Base
from sqlalchemy import text
from sqlalchemy.engine import Engine


class DatabaseConnection:
	def __init__(self, db_url=None):
		url = db_url or DATABASE_URL
		
		if url.startswith('sqlite:///'):
			# 1. Извлекаем чистое имя файла (например, 'bot.db')
			db_filename = url.replace('sqlite:///', '')
			
			# 2. Магия pathlib: .parent берет путь к папке 'database', где лежит этот скрипт
			current_folder = Path(__file__).resolve().parent
			
			# 3. Соединяем путь к папке и имя файла (получится абсолютный путь до папки database/bot.db)
			absolute_db_path = current_folder / db_filename
			
			# 4. Собираем финальный URL для SQLAlchemy
			self.db_url = f"sqlite:///{absolute_db_path}"
		else:
			self.db_url = url

		# Дальше стандартный запуск движка
		connect_args = {'check_same_thread': False} if self.db_url.startswith('sqlite') else {}
		self.engine = create_engine(self.db_url, connect_args=connect_args, future=True)
		self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False, future=True)
		
		# Создаем таблицы внутри database/bot.db
		Base.metadata.create_all(self.engine)
		
		#self._migrate_old_db()
		
	def _migrate_old_db(self):
		with self.SessionLocal() as session:
			try:
				session.execute(text("SELECT backup_server FROM users LIMIT 1"))
			except Exception:
				# Если упало с ошибкой — значит колонки нет, добавляем её!
				logger.info("Старая БД обнаружена. Добавляю колонку backup_server...")
				try:
					# ALTER TABLE добавляет колонку и сразу ставит всем старым юзерам 'fi-1'
					session.execute(text("ALTER TABLE users ADD COLUMN backup_server TEXT NOT NULL DEFAULT 'none'"))
					# Также создаем индекс для этой колонки, так как Base.metadata его не создаст на существующей таблице
					session.execute(text("CREATE INDEX IF NOT EXISTS idx_user_server ON users(backup_server)"))
					session.commit()
					logger.info("Миграция базы данных успешно завершена!")
				except Exception as e:
					session.rollback()
					logger.error(f"Ошибка при миграции БД: {e}")

	# Оптимизация SQLite: автоматический WAL-режим при каждом коннекте
	@event.listens_for(Engine, "connect")
	def set_sqlite_pragma(dbapi_connection, connection_record):
		cursor = dbapi_connection.cursor()
		cursor.execute("PRAGMA journal_mode=WAL")
		cursor.execute("PRAGMA synchronous=NORMAL")
		cursor.close()

	@contextmanager
	def session_scope(self):
		"""Безопасный контекстный менеджер транзакций"""
		session = self.SessionLocal()
		try:
			yield session
			session.commit()
		except Exception as e:
			session.rollback()
			logger.error(f'DB transaction error: {e}')
			raise
		finally:
			session.close()