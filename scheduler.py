import schedule
import time
import threading

from logger import logger

from database import database_manager
from servers import server_manager
import handlers


def run_schedule():
	while True:
		schedule.run_pending()
		time.sleep(60)


def daily_job():
	result = database_manager.bulk_decrease_days()
	# TODO Сделать удаление каскадным, на сервере (пересылать серверам id юзеров, которым нужно удалить ссылки)
	# пока пользователей мало это решение будет работать
	"""Удаляем неиспользуеммые ссылки у пользователей"""
	used_servers = set()
	all_user_ids = database_manager.get_all_user_ids()
	for user_id in all_user_ids:
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
				api_client = server_manager.get_api_server(server_id)
				time.sleep(0.05)
				query = api_client.user_exists(user_id)
				if query['exists']:
					api_client.delete_user(user_id)



	logger.info(f"Уменьшено дней у {result} польз.")
	

def start_scheduler():
	schedule.every().day.at('00:00').do(daily_job)
	threading.Thread(target=run_schedule, daemon=True).start()
	logger.info('Фоновый процесс запущен')
