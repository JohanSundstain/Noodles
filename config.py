import os
from local_secrets import (
	token, admin_id, 
	owner_id, number,
	api_key, bot_name)

TOKEN = token
ADMIN_ID = admin_id
OWNER_ID = owner_id
NUMBER = number
BONUS = 30
BOT_LINK = f't.me/{bot_name}'
API_TOKEN = api_key

DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///bot.db')

BUY_BUTTON = "💳 Купить подписку"
AMDINS_LINK_BUTTON = "📌 Админская ссылка"
STATISTIC_BUTTON = "📈 Статистика"
TEMP_LINK_BUTTON = "🔗 Временная ссылка"
STATUS_BUTTON = "🗂 Статус"
REF_BUTTON = "🔗 Реферальная ссылка"
HELP_BUTTON = "🔍 Справка"
LOCATION_BUTTON = "🌏 Выбрать локацию"

PRICES = {1: 100, 3: 250, 6: 450, -1: 0}
DAYS = {1: 30, 3: 90, 6: 180, -1: 1}
