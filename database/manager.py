from sqlalchemy import select, func, update
from .connection import DatabaseConnection
from .models import User, Referral
from config import BONUS

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
		
	def get_user_server_id(self, user_id: int)->str:
		with self.session_scope() as session:
			user = session.get(User, user_id)  
			return user.current_server

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

			# 2. Уменьшаем дни одним эффективным SQL-запросом ко всем сразу
			session.execute(
				update(User)
				.where(User.paid_days > 0)
				.values(paid_days=User.paid_days - 1)
			)
			
			return list(expired_users)

	# --- Твоя новая логика балансировки ---
	def get_servers_load(self, server_ids: list[str]) -> dict[str, int]:
		"""Возвращает количество активных пользователей на указанных серверах"""
		with self.session_scope() as session:
			result = session.execute(
				select(User.current_server, func.count(User.user_id))
				.where(User.current_server.in_(server_ids))
				.group_by(User.current_server)
			).all()
			return dict(result) # Вернет {'de-1': 142, 'de-2': 98}

	def update_user_server(self, user_id: int, server_id: str) -> None:
		with self.session_scope() as session:
			user = session.get(User, user_id)
			if user:
				user.current_server = server_id