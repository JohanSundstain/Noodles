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

        # создаём папку под БД (если нет)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._init_tables()
        self._enable_wal()

    # ----------------------------
    # CORE CONNECTION
    # ----------------------------
    @contextmanager
    def connect(self):
        conn = sqlite3.connect(
            self.db_path,
            timeout=30,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"DB transaction error: {e}")
            raise
        finally:
            conn.close()

    # ----------------------------
    # INIT
    # ----------------------------
    def _init_tables(self):
        try:
            with self.connect() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        paid_days INTEGER DEFAULT 0
                    )
                """)

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS referrals (
                        user_id INTEGER PRIMARY KEY,
                        inviter INTEGER,
                        reward_given BOOLEAN DEFAULT FALSE
                    )
                """)

            logger.info("SQLite tables initialized")

        except Exception as e:
            logger.error(f"DB init error: {e}")
            raise

    def _enable_wal(self):
        """Сильно уменьшает lock'и и повышает стабильность под нагрузкой"""
        try:
            with self.connect() as conn:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception as e:
            logger.warning(f"WAL enable failed: {e}")

    # ----------------------------
    # LOW LEVEL API
    # ----------------------------
    def execute(self, query, params=None):
        with self.connect() as conn:
            cur = conn.execute(query, params or ())
            return cur

    def fetch_one(self, query, params=None):
        with self.connect() as conn:
            cur = conn.execute(query, params or ())
            return cur.fetchone()

    def fetch_all(self, query, params=None):
        with self.connect() as conn:
            cur = conn.execute(query, params or ())
            return cur.fetchall()

    # ----------------------------
    # LOGIC
    # ----------------------------
    def check_user(self, user_id):
        row = self.fetch_one(
            "SELECT 1 FROM users WHERE user_id=?",
            (user_id,)
        )
        return row is not None

    def create_new_user(self, user_id, ref=None):
        if self.check_user(user_id):
            return

        self.execute(
            "INSERT INTO users (user_id) VALUES (?)",
            (user_id,)
        )

        if ref is not None and not self.check_user(ref):
            ref = None

        if ref is not None:
            self.execute(
                "INSERT INTO referrals (user_id, inviter) VALUES (?, ?)",
                (user_id, ref)
            )
        else:
            self.execute(
                "INSERT INTO referrals (user_id) VALUES (?)",
                (user_id,)
            )

    def create_subscription(self, user_id, days):
        if not self.check_user(user_id):
            return

        self.execute(
            "UPDATE users SET paid_days = paid_days + ? WHERE user_id=?",
            (days, user_id)
        )

        row = self.fetch_one(
            "SELECT inviter, reward_given FROM referrals WHERE user_id=?",
            (user_id,)
        )

        if not row:
            return

        inviter, reward_given = row

        if inviter and not reward_given and days > 1:
            try:
                send_temp_message(
                    bot,
                    inviter,
                    f"✅ Бонус {BONUS} дней за инвайт получен!",
                    120
                )

                self.execute(
                    "UPDATE users SET paid_days = paid_days + ? WHERE user_id=?",
                    (BONUS, inviter)
                )

                self.execute(
                    "UPDATE referrals SET reward_given=1 WHERE user_id=?",
                    (user_id,)
                )

            except Exception as e:
                logger.error(f"Referral bonus error: {e}")

    def get_paid_days(self, user_id):
        row = self.fetch_one(
            "SELECT paid_days FROM users WHERE user_id=?",
            (user_id,)
        )
        return row["paid_days"] if row else 0

    def reduce_days(self):
        users = self.fetch_all(
            "SELECT user_id, paid_days FROM users"
        )

        for row in users:
            user_id = row["user_id"]
            paid_days = row["paid_days"] - 1

            if paid_days <= 0:
                paid_days = 0

                bot.send_message(
                    user_id,
                    "⚠️ Ваша подписка истекла.\nУдалите бота если не хотите получать уведомления."
                )

                logger.info(f"Subscription expired: {user_id}")

                self.execute(
                    "UPDATE users SET paid_days=0 WHERE user_id=?",
                    (user_id,)
                )

                delete_users_link(user_id)

            else:
                logger.info(f"User {user_id}: days left {paid_days}")

                self.execute(
                    "UPDATE users SET paid_days=? WHERE user_id=?",
                    (paid_days, user_id)
                )