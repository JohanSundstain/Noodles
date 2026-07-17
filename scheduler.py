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
	logger.info(f"Осталься один день у {expired_users} польз.")

	"""Удаляем ссылки тех, у кого закончилась подписка"""
	deletion_dict = {}
	for user_id in expired_users:	
		"""Все остальные сервера"""

		bot.send_message(user_id, "⚠️ У вас закончилась подписка!")

		all_servers = set(server_manager.get_all_server_id())

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
				logger.info(f"server: {key}\ndeleted: {result['deleted']}\nfailed: {result['failed']}\nnot found: {result['not found']}")
			except Exception as e:
				logger.error(f"Ошибка создания запроса на удаление нескольких пользователей")

	"""Удаляем неиспользуеммые ссылки у пользователей"""
	used_servers = set()
	all_user_ids = set(database_manager.get_all_user_ids())
	remaining_users = all_user_ids - expired_users
	deletion_dict = {}
	for user_id in remaining_users:
		used_servers = set()
		"""Ссылки пользователей текущие"""
		used_servers.add(database_manager.get_user_server_id(user_id))
		used_servers.add(database_manager.get_user_server_id(user_id, main=False))

		"""Все остальные сервера"""
		all_servers = set(server_manager.get_all_server_id())

		"""Неиспользуемые сервера"""
		unused_servers = all_servers - used_servers
		for server_id in unused_servers:
			if server_id != 'none':
				if server_id in deletion_dict:
					deletion_dict[server_id].append(user_id)
				else:
					deletion_dict[server_id] = [user_id]

		for key, value in deletion_dict.items():
			try:
				api_client = server_manager.get_api_server(key)
				result = api_client.delete_users(value)
				logger.info(f"server: {key}\ndeleted: {result['deleted']}\nfailed: {result['failed']}\nnot found: {result['not found']}")
			except Exception as e:
				logger.error(f"Ошибка создания запроса на удаление нескольких пользователей")


def start_scheduler():
	schedule.every().day.at('00:00').do(daily_job)
	threading.Thread(target=run_schedule, daemon=True).start()
	logger.info('Фоновый процесс запущен')
