
from database import database_manager
from servers import server_manager
import time

def func():
	users = database_manager.get_all_user_ids()
	api = server_manager.get_api_server("fi-1")
	for user_id in users:
		id = database_manager.get_user_server_id(user_id)
		if id == 'fi-1':	
			time.sleep(1)
			api.create_user(user_id)
