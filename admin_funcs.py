
from database import database_manager
from servers import server_manager
import time

from utils import (
	send_temp_message
)

from config import OWNER_ID

from bot import bot

def func():
	users = database_manager.get_all_user_ids()
	api = server_manager.get_api_server("fi-1")
	for user_id in users:
		id = database_manager.get_user_server_id(user_id)
		if id == 'fi-1':	
			time.sleep(1)
			api.create_user(user_id)


def get_info(user_id):
	server_id = database_manager.get_user_server_id(user_id)
	paid_days =	database_manager.get_paid_days(user_id)
	api_client = server_manager.get_api_server(server_id)
	answer = api_client.user_exists(user_id)
	is_on_server = 'false'
	if answer["exists"]:
		is_on_server = "true"
	
	send_temp_message(bot, OWNER_ID, f"server ID: {server_id}\nPlan: {paid_days}", 30)

def is_on_server(user_id, server_id):
	api_client = server_manager.get_api_server(server_id)
	answer = api_client.user_exists(user_id)
	is_on_server = 'false'
	if answer["exists"]:
		is_on_server = 'true'

	send_temp_message(bot, OWNER_ID, f"server ID: {server_id}\nis on server: {is_on_server}", 30)

def set_server(user_id, server_id):
	old_server_id = database_manager.get_user_server_id(user_id)
	if old_server_id != 'none':
		api_server = server_manager.get_api_server(old_server_id)
		api_server.schedule_delete(user_id, 600)

	api_server = server_manager.get_api_server(server_id)
	database_manager.update_user_server(user_id, server_id)
	answer = api_server.create_user(user_id)
	if answer['status'] == "ok":
		send_temp_message(bot, OWNER_ID, f"servers success: {user_id}", 30)
	else:
		send_temp_message(bot, OWNER_ID, f"servers failed: {user_id}", 30)

	new_server_id = database_manager.get_user_server_id(user_id)
	if new_server_id == server_id:
		send_temp_message(bot, OWNER_ID, f"success: {user_id}", 30)
	else:
		send_temp_message(bot, OWNER_ID, f"failed: {user_id}", 30)
		

def reduce_days(user_id, days):
	prev_days = database_manager.get_paid_days(user_id)
	database_manager.decrease_days(user_id, days)
	new_days = database_manager.get_paid_days(user_id)
	if prev_days == new_days:
		send_temp_message(bot, OWNER_ID, f"failed: {prev_days}->{new_days}", 30)
	else:
		send_temp_message(bot, OWNER_ID, f"success: {prev_days}->{new_days}", 30)

def server_load(server_id):
	server_load = database_manager.get_servers_load([server_id])
	send_temp_message(bot, OWNER_ID, f"{server_load}", 30)
	