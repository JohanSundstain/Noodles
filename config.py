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

BUTTONS = {
	"buy" 		: 	"💳 Купить подписку",
	"statistic" : 	"📈 Статистика",
	"temp" 		: 	"🔗 Временная ссылка",
	"status" 	:	"🗂 Статус",
	"ref" 		:	"🔗 Реферальная ссылка",
	"help" 		: 	"🔍 Справка",
	"location" 	: 	"🌏 Выбрать локацию"
}

PLANS = [
 {"price" : 100, "days" : 30},
#{"price" : 100, "days" : 30},
#{"price" : 100, "days" : 30}
]
