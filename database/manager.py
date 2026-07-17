from sqlalchemy import select, func, update
from .connection import DatabaseConnection
from .models import User, Referral, Transactions
from config import BONUS

from datetime import datetime, timezone

class DatabaseManager(DatabaseConnection):
	
	def check_user(self, user_id: int) -> bool:
		with self.session_scope() as session:
			return session.get(User, user_id) is not None

	def create_new_user(self, user_id: int, ref_id: int | None = None) -> None:
		with self.session_scope() as session:
			if session.get(User, user_id):
				return

			# Проверяем, существует ли пригласитель
			if ref_id is not None and session.get(User, ref_id) is None:
				ref_id = None

			session.add(User(user_id=user_id))
			session.add(Referral(user_id=user_id, inviter=ref_id))

	def get_paid_days(self, user_id: int) -> int:
		with self.session_scope() as session:
			user = session.get(User, user_id)
			return user.paid_days if user else 0
		
	
	def get_user_server_id(self, user_id: int, main: bool=True)->str:
		with self.session_scope() as session:
			user = session.get(User, user_id)
			if main:
				return user.current_server if user else None
			else:
				return user.backup_server if user else None
			
	
	def get_active_user_ids(self) -> list[int]:
		with self.session_scope() as session:
			user_ids = session.execute(select(User.user_id).where(User.paid_days > 0)).scalars().all()
			return user_ids
	
		
	def get_all_user_ids(self) -> list[int]:
		with self.session_scope() as session:
			result = session.execute(select(User.user_id)).scalars().all()
			return result
		

	def create_subscription(self, user_id: int, days: int) -> dict | None:
		"""Начисляет дни. Если положен бонус рефералу — возвращает данные для отправки сообщения"""
		with self.session_scope() as session:
			user = session.get(User, user_id)
			if not user:
				return None

			user.paid_days += days
			referral = session.get(Referral, user_id)
			
			if referral and referral.inviter and not referral.reward_given and days > 1:
				inviter = session.get(User, referral.inviter)
				if inviter:
					inviter.paid_days += BONUS
					referral.reward_given = True
					# Возвращаем данные наружу, чтобы НЕ слать сообщения внутри транзакции
					return {"inviter_id": inviter.user_id, "bonus_days": BONUS}
		return None

	def bulk_decrease_days(self) -> list[int]:
		"""Уменьшает дни всем активным юзерам за 1 быстрый запрос.
		Возвращает список ID тех, у кого подписка только что сгорела."""
		with self.session_scope() as session:
			# 1. Находим тех, у кого завтра подписка сгорит (было > 0, станет 0)
			expired_users = session.scalars(
				select(User.user_id).where(User.paid_days == 1)
			).all()

			session.execute(
				update(User)
				.where(User.paid_days == 1)
				.values(current_server='none', backup_server='none')
			)

			# 2. Уменьшаем дни одним эффективным SQL-запросом ко всем сразу
			session.execute(
				update(User)
				.where(User.paid_days > 0)
				.values(paid_days=User.paid_days - 1)
			)
			
			return list(expired_users)
		
	def decrease_days(self, user_id: int, days: int):
		with self.session_scope() as session:
			user = session.get(User, user_id)
			if user:
				user.paid_days -= days

	# --- Твоя новая логика балансировки ---
	def get_servers_load(self, server_ids: list[str], main: bool=True) -> dict[str, int]:
		"""Возвращает количество активных пользователей на указанных серверах"""
		with self.session_scope() as session:
			if main:
				result = session.execute(
					select(User.current_server, func.count(User.user_id))
					.where(User.current_server.in_(server_ids))
					.group_by(User.current_server)
				).all()
			else:
				result = session.execute(
					select(User.backup_server, func.count(User.user_id))
					.where(User.backup_server.in_(server_ids))
					.group_by(User.backup_server)
				).all()

			servers_load = dict(result)
			for id in server_ids:
				if id in servers_load:
					continue
				else:
					servers_load[id] = 0
					
			return servers_load # Вернет {'de-1': 142, 'de-2': 98}

	def update_user_server(self, user_id: int, server_id: str, main: bool=True) -> None:
		with self.session_scope() as session:
			user = session.get(User, user_id)
			if user:
				if main:
					user.current_server = server_id
				else:
					user.backup_server = server_id


	def get_month_sales(self, year: int, month: int) -> int:
		month_start = datetime(year=year, month=month, day=1, tzinfo=timezone.utc)

		if month == 12:
			"""Если декабрь, то начало следующего месяца это январь нового года"""
			next_month = datetime(year=year + 1,month=1,day=1,tzinfo=timezone.utc)
		else:
			next_month = datetime(year=year, month=month + 1, day=1,tzinfo=timezone.utc)

		with self.session_scope() as session:
			query = select(func.coalesce(func.sum(Transactions.amount),0)).where(
				Transactions.date >= month_start,
				Transactions.date < next_month)

			return session.scalar(query)
		
	def create_transaction(self, user_id: int, amount: int):
		with self.session_scope() as session:
			session.add(Transactions(user_id=user_id, amount=amount))