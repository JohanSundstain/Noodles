from contextlib import contextmanager

from bot import bot
from config import BONUS, DATABASE_URL
from logger import logger
from telegram_helpers import send_temp_message
from xray import delete_users_link
from sqlalchemy import Boolean, Column, Integer, create_engine, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True, autoincrement=False)
    paid_days = Column(Integer, default=0, nullable=False)
    referral = relationship('Referral', back_populates='user', uselist=False, cascade='all, delete-orphan')


class Referral(Base):
    __tablename__ = 'referrals'

    user_id = Column(Integer, ForeignKey('users.user_id'), primary_key=True)
    inviter = Column(Integer, nullable=True)
    reward_given = Column(Boolean, default=False, nullable=False)
    user = relationship('User', back_populates='referral')


class Database:
    def __init__(self, db_url=None):
        self.db_url = db_url or DATABASE_URL

        connect_args = {}
        if self.db_url.startswith('sqlite'):
            connect_args = {'check_same_thread': False}

        self.engine = create_engine(self.db_url, connect_args=connect_args, future=True)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False, future=True)

        self._init_tables()

    # ----------------------------
    # CORE CONNECTION
    # ----------------------------
    @contextmanager
    def session_scope(self):
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

    # ----------------------------
    # INIT
    # ----------------------------
    def _init_tables(self):
        try:
            Base.metadata.create_all(self.engine)
            logger.info('Database tables initialized')
        except Exception as e:
            logger.error(f'DB init error: {e}')
            raise

    # ----------------------------
    # LOGIC
    # ----------------------------
    def check_user(self, user_id):
        with self.session_scope() as session:
            return session.get(User, user_id) is not None

    def create_new_user(self, user_id, ref=None):
        with self.session_scope() as session:
            if session.get(User, user_id):
                return

            if ref is not None and session.get(User, ref) is None:
                ref = None

            session.add(User(user_id=user_id))
            session.add(Referral(user_id=user_id, inviter=ref))

    def create_subscription(self, user_id, days):
        with self.session_scope() as session:
            user = session.get(User, user_id)
            if not user:
                return

            user.paid_days = (user.paid_days or 0) + days

            referral = session.get(Referral, user_id)
            if referral and referral.inviter and not referral.reward_given and days > 1:
                try:
                    inviter = session.get(User, referral.inviter)
                    if inviter:
                        send_temp_message(
                            bot,
                            inviter,
                            f'✅ Бонус {BONUS} дней за инвайт получен!',
                            120
                        )
                        inviter.paid_days = (inviter.paid_days or 0) + BONUS
                        referral.reward_given = True
                except Exception as e:
                    logger.error(f'Referral bonus error: {e}')

    def get_paid_days(self, user_id):
        with self.session_scope() as session:
            user = session.get(User, user_id)
            return user.paid_days if user else 0

    def reduce_days(self):
        with self.session_scope() as session:
            users = session.query(User).all()

            for user in users:
                paid_days = (user.paid_days or 0) - 1

                if paid_days <= 0:
                    user.paid_days = 0
                    try:
                        bot.send_message(
                            user.user_id,
                            '⚠️ Ваша подписка истекла.\nУдалите бота если не хотите получать уведомления.'
                        )
                    except Exception as e:
                        logger.warning(f'Не удалось уведомить пользователя {user.user_id}: {e}')

                    logger.info(f'Subscription expired: {user.user_id}')
                    delete_users_link(user.user_id)
                else:
                    user.paid_days = paid_days
                    logger.info(f'User {user.user_id}: days left {paid_days}')

    def close(self):
        self.engine.dispose()