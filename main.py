import telebot
import random
import threading
import time
import sqlite3
import logging
import sys
import os
from telebot import types
from datetime import datetime, timedelta
import qrcode
from io import BytesIO
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
    from config import TOKEN, ADMIN_ID, OWNER_ID, PRICES, RESONS, NUMBER
except ImportError as e:
    logger.error(f"Ошибка импорта config: {e}")
    logger.error("Создайте файл config.py со следующими переменными:")
    logger.error("TOKEN, ADMIN_ID, OWNER_ID, PRICES, RESONS, NUMBER")
    sys.exit(1)

try:
    from utils import create_user, delete_user_by_name
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
                        username TEXT,
                        subscription_end TEXT
                    )
                """)
                self.connection.execute("""
                    CREATE TABLE IF NOT EXISTS payments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        username TEXT,
                        plan INTEGER,
                        status TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                # Добавление колонки created_at если её нет
                try:
                    self.connection.execute("ALTER TABLE payments ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                except sqlite3.OperationalError:
                    pass  # Колонка уже существует
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
    try:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("💳 Купить подписку", callback_data="buy"))
        markup.add(types.InlineKeyboardButton("📊 Мой статус", callback_data="status"))
        
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
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        user_id = message.from_user.id
        username = message.from_user.username or "no_username"
        
        plan = user_plan.get(user_id)
        
        if not plan:
            bot.send_message(user_id, "❗ Сначала выбери тариф")
            return
        
        # Создаём заявку в БД
        cur = db.execute(
            "INSERT INTO payments (user_id, username, plan, status) VALUES (?, ?, ?, ?)",
            (user_id, username, plan, "pending")
        )
        payment_id = cur.lastrowid
        
        file_id = message.photo[-1].file_id
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"approve:{payment_id}"),
            types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject:{payment_id}")
        )
        
        bot.send_photo(
            ADMIN_ID,
            file_id,
            caption=f"🆕 Оплата #{payment_id}\nUser: @{username}\nТариф: {plan} мес\nID: {user_id}",
            reply_markup=markup
        )
        
        bot.send_message(user_id, "⏳ Скрин получен, ожидайте проверки")
        logger.info(f"Пользователь {user_id} отправил скрин для тарифа {plan}")
        
    except Exception as e:
        logger.error(f"Ошибка в handle_photo для пользователя {message.from_user.id}: {e}")
        bot.send_message(message.from_user.id, "⚠️ Произошла ошибка при обработке фото. Попробуйте позже.")

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
            
            row = db.fetch_one("SELECT subscription_end FROM users WHERE user_id=?", (user_id,))
            
            if not row:
                bot.send_message(user_id, "❌ У вас нет активной подписки")
                bot.answer_callback_query(call.id)
                return
            
            end_date = datetime.fromisoformat(row[0])
            
            if end_date < datetime.now():
                bot.send_message(user_id, "❌ Подписка истекла")
            else:
                bot.send_message(
                    user_id,
                    f"✅ Подписка активна до {end_date.strftime('%Y-%m-%d %H:%M')}"
                )
            
            bot.answer_callback_query(call.id)
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
            payment_id = int(data.split(":")[1])
            
            row = db.fetch_one("SELECT user_id, plan FROM payments WHERE id=?", (payment_id,))
            
            if not row:
                bot.answer_callback_query(call.id, "❌ Платёж не найден", show_alert=True)
                return
            
            user_id, plan = row
            plan_months = int(plan)
            
            row = db.fetch_one("SELECT subscription_end FROM users WHERE user_id=?", (user_id,))
            
            now = datetime.now()
            
            if row and row[0]:
                try:
                    current_end = datetime.fromisoformat(row[0])
                    base_date = current_end if current_end > now else now
                except (ValueError, TypeError):
                    base_date = now
            else:
                base_date = now
            
            new_end = base_date + timedelta(days=30 * plan_months)
            
            # Обновление подписки
            db.execute(
                "INSERT OR REPLACE INTO users (user_id, username, subscription_end) VALUES (?, ?, ?)",
                (user_id, "unknown", new_end.isoformat())
            )
            
            db.execute("UPDATE payments SET status='approved' WHERE id=?", (payment_id,))
            
            # Генерация ссылки
            try:
                vless_url = create_user(user_id)
                
                if vless_url:
                    # Генерация QR-кода
                    try:
                        img = qrcode.make(vless_url)
                        buffer = BytesIO()
                        img.save(buffer, format="PNG")
                        buffer.seek(0)
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
                f"✅ Подписка продлена до {new_end.strftime('%Y-%m-%d %H:%M')}"
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
            payment_id = int(data.split(":")[1])
            
            row = db.fetch_one("SELECT user_id FROM payments WHERE id=?", (payment_id,))
            
            if not row:
                bot.answer_callback_query(call.id, "❌ Платёж не найден", show_alert=True)
                return
            
            user_id = row[0]
            
            db.execute("UPDATE payments SET status='rejected' WHERE id=?", (payment_id,))
            
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

# -------------------------
# ФОНТОВЫЙ ПРОЦЕСС С ОТКАЗОУСТОЙЧИВОСТЬЮ
# -------------------------
def notify_expiring_subscriptions():
    """Фоновый процесс с отказоустойчивостью"""
    while True:
        try:
            now = datetime.now()
            rows = db.fetch_all("SELECT user_id, subscription_end FROM users")
            
            for row in rows:
                try:
                    user_id = row['user_id'] if hasattr(row, 'keys') else row[0]
                    end = row['subscription_end'] if hasattr(row, 'keys') else row[1]
                    
                    if not end:
                        continue
                    
                    end_date = datetime.fromisoformat(end)
                    
                    if end_date < now:
                        try:
                            bot.send_message(
                                user_id,
                                "❌ Ваша подписка истекла"
                            )
                        except Exception as e:
                            logger.warning(f"Не удалось отправить уведомление пользователю {user_id}: {e}")
                        
                        db.execute("DELETE FROM users WHERE user_id=?", (user_id,))
                        
                        # Удаление пользователя
                        try:
                            delete_user_by_name(user_id)
                        except Exception as e:
                            logger.error(f"Ошибка удаления пользователя {user_id}: {e}")
                            
                except Exception as e:
                    logger.error(f"Ошибка обработки пользователя: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Ошибка в фоновом процессе: {e}")
            
        time.sleep(3600)  # Проверка раз в час

# -------------------------
# RUN С ОТКАЗОУСТОЙЧИВОСТЬЮ
# -------------------------
if __name__ == "__main__":
    try:
        logger.info("Запуск бота...")
        
        # Запуск фонового процесса
        thread = threading.Thread(
            target=notify_expiring_subscriptions,
            daemon=True
        )
        thread.start()
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