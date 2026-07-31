import re
import subprocess
from config import ADMIN_ID, OWNER_ID


from logger import logger
from cache import user_index_cache

# ------------------------
# CORE LOGIC
# ------------------------

def generate_secure_code(n : int) -> int:
	return ''.join(__import__('secrets').choice('0123456789') for _ in range(n))

def is_admin(user_id):
	return user_id == ADMIN_ID

def is_owner(user_id):
	return user_id == OWNER_ID

def load_user_dict():
	"""Загружает список пользователей из системы и строит словарь {uid: index}."""
	result = subprocess.run(
		['userlist'],
		capture_output=True,
		text=True,
		encoding='utf-8',
		timeout=10
	)

	
	if result.returncode != 0:
		logger.error(f'userlist failed: {result.stderr}')
		return {}

	users_list = re.findall(r'\d+\.\s+(\w+)', result.stdout or "")
	return {uid: i for i, uid in enumerate(users_list, start=1)}


def get_user_index(user_id):
	"""Возвращает индекс пользователя в системе (из кэша или утилиты)."""
	return user_index_cache.get(str(user_id), load_user_dict)

def get_user_index_str(user_id_str):
	return user_index_cache.get(user_id_str, load_user_dict)


def load_user_link(user_id):
	"""Получает vless-ссылку для существующего пользователя по sharelink."""
	try:
		if is_admin(user_id) or is_owner(user_id):
			user_index = 1 # главвная ссыка
		else:
			user_index = get_user_index(user_id)
		if not user_index:
			logger.warning(f'User index not found for user_id: {user_id}')
			return None

		result = subprocess.run(
			['sharelink'], 
			input=f'{user_index}\n',
			capture_output=True,
			text=True,
			encoding='utf-8',
			timeout=10
		)

		if result.returncode != 0:
			logger.error(f'sharelink failed for {user_id}: {result.stderr or result.stdout}')
			return None

		url = re.search(r'vless://[^\s]+', result.stdout or "")
		return url.group() if url else None

	except Exception as e:
		# Безопасный лог через user_id во избежание UnboundLocalError
		logger.error(f'sharelink error for user {user_id}: {e}')
		return None


def create_external_user(user_id):
	"""Создает нового пользователя в системе."""
	try:
		# Приведение к str для консистентности с get_user_index
		if user_index_cache.is_cached(str(user_id)):
			logger.error(f'Пользователь {user_id} уже существует в кэше')
			return None
		
		result = subprocess.run(
			['newuser'],
			input=f'{user_id}\n',
			capture_output=True,
			text=True,
			encoding='utf-8',
			timeout=10
		)

		if result.returncode != 0:
			logger.error(f'newuser failed for {user_id}: {result.stderr or result.stdout}')
			return None

		url = re.search(r'vless://[^\s]+', result.stdout or "")
		return url.group() if url else None

	except Exception as e:
		logger.error(f'newuser error {user_id}: {e}')
		return None


def remove_external_user(user_index):
	"""Удаляет пользователя по его системному индексу."""
	try:
		result = subprocess.run(
			['rmuser'],
			input=f'{user_index}\n',
			capture_output=True,
			text=True,
			encoding='utf-8',
			timeout=10
		)

		logger.info(f'rmuser output for index {user_index}\nstdout: {result.stdout}\nstderr: {result.stderr}')

		if result.returncode != 0:
			return False

		return True

	except Exception as e:
		logger.error(f'rmuser error {user_index}: {e}')
		return False
	
