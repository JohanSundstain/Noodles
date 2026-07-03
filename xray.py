import re
import subprocess
import threading
from logger import logger

from cache import Cache

user_index_cache = Cache(ttl=120)

def _to_str(user_id):
	return str(user_id)

def create_user(user_id):
	user_id_str = _to_str(user_id)

	if check_user(user_id):
		return load_user_link(user_id)

	result = subprocess.run(
		['newuser'],
		input=user_id_str + '\n',
		capture_output=True,
		text=True,
		encoding='utf-8',
	)

	url = re.search(r'vless://[^\s]+', result.stdout)
	if url:
		return url.group()

	logger.error(f'Не удалось получить VLESS-ссылку для пользователя {user_id}')
	return None


def load_user_dict():
	result = subprocess.run(
		['userlist'],
		input='',
		capture_output=True,
		text=True,
		encoding='utf-8')

	users_list = re.findall(r'\d+\.\s+(\w+)', result.stdout)
	users_dict = {}
	for i in range(len(users_list)):
		user_id_str = users_list[i] 
		users_dict[user_id_str] = i + 1 

	return users_dict

def get_user_index(user_id):
	user_id_str = str(user_id)
	return user_index_cache.get(user_id_str, load_user_dict)

def check_user(user_id):
	user_id_str = _to_str(user_id)
	return user_index_cache.is_cached(user_id_str)

def delete_users_link(user_id):
	user_id_str = _to_str(user_id)
	user_index = user_index_cache.get(user_id_str, load_user_dict)

	if user_index is None:
		logger.warning(f'Пользователь {user_id_str} не найден.')
		return None

	process = subprocess.Popen(
		['rmuser'],
		stdin=subprocess.PIPE,
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE,
		text=True,
		encoding='utf-8',
	)

	stdout, stderr = process.communicate(f'{user_index}\n')
	if process.returncode != 0:
		logger.warning(f'Ошибка rmuser для {user_id_str}: {stderr.strip()}')


def load_user_link(user_id):
	user_id_str = _to_str(user_id)

	user_index = user_index_cache.get(user_id_str, load_user_dict)

	if user_index is None:
		logger.warning(f'Пользователь {user_id_str} не найден.')
		return None

	process = subprocess.Popen(
		['sharelink'],
		stdin=subprocess.PIPE,
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE,
		text=True,
		encoding='utf-8',
	)

	stdout, stderr = process.communicate(f'{user_index}\n')
	url = re.search(r'vless://[^\s]+', stdout)
	if url:
		return url.group()

	logger.error(f'Не удалось получить ссылку пользователя {user_id}')
	return None


def schedule_user_deletion(user_id, seconds=3600):
	def delete():
		try:
			delete_users_link(user_id)
		except Exception as e:
			logger.error(f'Ошибка удаления временной ссылки для {user_id}: {e}')

	threading.Timer(seconds, delete).start()
