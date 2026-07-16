from sqlalchemy import Integer, Boolean, ForeignKey, String, Index, DateTime
from datetime import datetime, timezone

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
	pass

class User(Base):
	__tablename__ = 'users'

	user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
	paid_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
	
	# Поле для нашей балансировки серверов (из прошлых шагов)
	current_server: Mapped[str] = mapped_column(String, default='none', nullable=False)
	backup_server: Mapped[str] = mapped_column(String, default='none', nullable=False)

	# Связь один-к-одному с таблицей рефералов
	referral = relationship('Referral', back_populates='user', uselist=False, cascade='all, delete-orphan')


class Referral(Base):
	__tablename__ = 'referrals'

	user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.user_id'), primary_key=True)
	inviter: Mapped[int | None] = mapped_column(Integer, nullable=True)
	reward_given: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

	user = relationship('User', back_populates='referral')
	

class Transactions(Base):
	__tablename__ = 'transactions'
	
	transaction_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.user_id'))
	amount: Mapped[int | None] = mapped_column(Integer, nullable=True)	
	date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),  nullable=False)

# Индекс для мгновенного подсчета юзеров на серверах через GROUP BY
Index('idx_user_server', User.current_server)