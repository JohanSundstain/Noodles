import telebot
import threading
import time
import sqlite3
from telebot import types
from datetime import datetime, timedelta
import qrcode
from io import BytesIO

from Noodles.config import TOKEN, ADMIN_ID, OWNER_ID, PRICES
#from utils import create_user, delete_user_by_name

bot = telebot.TeleBot(TOKEN)

# -------------------------
# SQLITE INIT
# -------------------------
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
	user_id INTEGER PRIMARY KEY,
	username TEXT,
	subscription_end TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS payments (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	user_id INTEGER,
	username TEXT,
	plan INTEGER,
	status TEXT
)
""")

conn.commit()

# временный выбор тарифа
user_plan = {}

# -------------------------
# START MENU
# -------------------------
@bot.message_handler(commands=['start'])
def start(message):
	markup = types.InlineKeyboardMarkup()

	markup.add(types.InlineKeyboardButton("💳 Купить подписку", callback_data="buy"))
	markup.add(types.InlineKeyboardButton("📊 Мой статус", callback_data="status"))

	bot.send_message(
		message.chat.id,
		"Добро пожаловать 👇",
		reply_markup=markup
	)


# -------------------------
# PHOTO (скрин оплаты)
# -------------------------
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
	user_id = message.from_user.id
	username = message.from_user.username or "no_username"

	plan = user_plan.get(user_id)

	if not plan:
		bot.send_message(user_id, "❗ Сначала выбери тариф")
		return

	# создаём заявку БЕЗ фото в БД
	cursor.execute("""
		INSERT INTO payments (user_id, username, plan, status)
		VALUES (?, ?, ?, ?)
	""", (user_id, username, plan, "pending"))

	conn.commit()

	payment_id = cursor.lastrowid
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


# -------------------------
# CALLBACKS
# -------------------------
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
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

		cursor.execute("""
			SELECT subscription_end 
			FROM users 
			WHERE user_id=?
		""", (user_id,))

		row = cursor.fetchone()

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
				f"✅ Подписка активна до {end_date.strftime('%Y-%m-%d')}"
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
			f"Вы выбрали {plan} мес.\nОтправьте скрин оплаты."
		)

		bot.answer_callback_query(call.id)
		return

	# -------------------------
	# APPROVE
	# -------------------------
	if data.startswith("approve:"):
		payment_id = int(data.split(":")[1])

		cursor.execute("SELECT user_id, plan FROM payments WHERE id=?", (payment_id,))
		row = cursor.fetchone()

		if not row:
			return

		user_id, plan = row
		plan_months = int(plan)

		cursor.execute("SELECT subscription_end FROM users WHERE user_id=?", (user_id,))
		row = cursor.fetchone()

		now = datetime.now()

		if row and row[0]:
			current_end = datetime.fromisoformat(row[0])

			base_date = current_end if current_end > now else now
		else:
			base_date = now

		new_end = base_date + timedelta(days=30 * plan_months)

		cursor.execute("""
			INSERT OR REPLACE INTO users (user_id, username, subscription_end)
			VALUES (?, ?, ?)
		""", (user_id, "unknown", new_end.isoformat()))

		cursor.execute("UPDATE payments SET status='approved' WHERE id=?", (payment_id,))
		conn.commit()

		vless_url = "some url" # create_user(user_id)
		img = qrcode.make(vless_url)

		buffer = BytesIO()
		img.save(buffer, format="PNG")
		buffer.seek(0)

		bot.send_photo(user_id, buffer)

		bot.send_message(
			user_id,
			f"```\n{vless_url}```\n",
			parse_mode="Markdown")

		bot.send_message(
			user_id,
			f"✅ Подписка продлена до {new_end.strftime('%Y-%m-%d')}"
		)

		bot.edit_message_caption(
			chat_id=ADMIN_ID,
			message_id=call.message.message_id,
			caption="✅ ПОДТВЕРЖДЕНО"
		)
		
		bot.send_message(OWNER_ID,
				f"✅ Куплена подписка на сумму {PRICES[int(plan)]}")

		bot.answer_callback_query(call.id)
		return

	# -------------------------
	# REJECT (ИСПРАВЛЕНО)
	# -------------------------
	if data.startswith("reject:"):
		payment_id = int(data.split(":")[1])

		cursor.execute("SELECT user_id FROM payments WHERE id=?", (payment_id,))
		row = cursor.fetchone()

		if not row:
			return

		user_id = row[0]

		cursor.execute("UPDATE payments SET status='rejected' WHERE id=?", (payment_id,))
		conn.commit()

		bot.send_message(
			user_id,
			"❌ Оплата отклонена. Попробуйте ещё раз или свяжитесь с поддержкой."
		)

		bot.edit_message_caption(
			chat_id=ADMIN_ID,
			message_id=call.message.message_id,
			caption="❌ ОТКЛОНЕНО"
		)

		bot.answer_callback_query(call.id)
		return


def notify_expiring_subscriptions():
	while True:
		now = datetime.now()

		cursor.execute("""
			SELECT user_id, subscription_end 
			FROM users
		""")
		rows = cursor.fetchall()

		for user_id, end in rows:
			if not end:
				continue

			end_date = datetime.fromisoformat(end)

			days_left = (end_date - now).days

			if end_date < now:
				bot.send_message(
					user_id,
					"❌ Ваша подписка истекла"
				)

			cursor.execute("DELETE FROM users WHERE user_id=?", (user_id,))
			conn.commit()
			#delete_user_by_name(user_id)

		time.sleep(3600)

# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
	threading.Thread(
		target=notify_expiring_subscriptions,
		daemon=True
	).start()
	bot.infinity_polling()