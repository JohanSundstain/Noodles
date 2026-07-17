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
	expired_users = set(database_manager.bulk_decrease_days())
	logger.info(f"Осталься один день у {list(expired_users)} польз.")

	"""Удаляем ссылки тех, у кого закончилась подписка"""
	deletion_dict = {}
	for user_id in list(expired_users):	
		"""Все остальные сервера"""

		bot.send_message(user_id, "⚠️ У вас закончилась подписка!")

		all_servers = server_manager.get_all_server_id()

		for server_id in all_servers:
			if server_id != 'none':
				if server_id in deletion_dict:
					deletion_dict[server_id].append(user_id)
				else:
					deletion_dict[server_id] = [user_id]

	for key, value in deletion_dict.items():
		try:
			api_client = server_manager.get_api_server(key)
			result = api_client.delete_users(value)
			logger.info(f"=====SERVER ID===== {key}")
			logger.info(f"deleted: {result['deleted']}\nfailed: {result['failed']}\nnot found: {result['not_found']}")
		except Exception as e:
			logger.error(f"Ошибка создания запроса на удаление нескольких пользователей: {e}")


def start_scheduler():
	schedule.every().day.at('00:00').do(daily_job)
	threading.Thread(target=run_schedule, daemon=True).start()
	logger.info('Фоновый процесс запущен')
