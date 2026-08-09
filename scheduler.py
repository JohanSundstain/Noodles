import schedule
import time
import threading

from logger import logger

from database import database_manager
from servers import server_manager
from bot import bot
import handlers


def run_schedule():
	while True:
		schedule.run_pending()
		time.sleep(60)

def daily_job():
	expired_users, almost_expired_users = database_manager.bulk_decrease_days()
	logger.info(f"Осталься один день у {list(expired_users)} польз.")

	"""Пишем тем, у кого подчти кончилась подписка"""
	for user_id in almost_expired_users:	
		"""Все остальные сервера"""
		bot.send_message(user_id, "⚠️ Ваша подписка истекает через 3 дня")

	"""Удаляем ссылки тех, у кого закончилась подписка"""
	for user_id in expired_users:	
		"""Все остальные сервера"""

		bot.send_message(user_id, "⚠️ У вас закончилась подписка!")

	if expired_users != []:
		all_servers = server_manager.get_all_api()
		for server_id in all_servers:
			if server_id.id != 'none':
				server_id.delete_user(expired_users)


def start_scheduler():
	schedule.every().day.at('00:00').do(daily_job)
	threading.Thread(target=run_schedule, daemon=True).start()
	logger.info('Фоновый процесс запущен')
