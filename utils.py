import subprocess
import threading
import secrets
import time
import re
import logging
import qrcode
import sys
from io import BytesIO

# Настройка логирования
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
	handlers=[
		logging.FileHandler('bot.log'),
		logging.StreamHandler(sys.stdout)
	]
)

logger = logging.getLogger(__name__)

def create_user(user_id):
	user_id_str = str(user_id)

	if check_user(user_id):
		return get_users_link(user_id)
	else:
		# Передаем ввод через параметр input
		result = subprocess.run(
			['newuser'],  # или ['/path/to/program']
			input= user_id_str +'\n',
			capture_output=True,
			text=True,
			encoding='utf-8'
		)

		url = re.search(r'vless://[^\s]+', result.stdout)
		if url:
			return url.group()


def get_user_list():
	result = subprocess.run(
		['userlist'],
		input="",
		capture_output=True,
		text=True,
		encoding='utf-8'
	)

	users = re.findall(r'\d+\.\s+(\w+)', result.stdout)
	return users

def check_user(user_id):
	user_id_str = str(user_id)
	users = get_user_list()

	return user_id_str in users


def delete_users_link(user_id):
	"""Удаляет пользователя по имени"""

	user_id_str = str(user_id)
	users = get_user_list()
	
	if user_id_str not in users:
		print(f"Пользователь {user_id_str} не найден")
		return
	
	# Находим номер пользователя
	user_number = users.index(user_id_str) + 1
	
	# Запускаем rmuser и отправляем номер
	process = subprocess.Popen(
		['rmuser'],
		stdin=subprocess.PIPE,
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE,
		text=True,
		encoding='utf-8'
	)
	
	stdout, stderr = process.communicate(f"{user_number}\n")


def get_users_link(user_id):
	user_id_str = str(user_id)

	users = get_user_list()

	if user_id_str not in users:
		print(f"Пользователь {user_id_str} не найден")
		return
	
	user_number = users.index(user_id_str) + 1

	process = subprocess.Popen(
		['sharelink'],
		stdin=subprocess.PIPE,
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE,
		text=True,
		encoding='utf-8'
	)

	stdout, stderr = process.communicate(f"{user_number}\n")

	url = re.search(r'vless://[^\s]+', stdout)
	if url:
		return url.group()
	

def qrcode_generate(url):
	img = qrcode.make(url)
	buffer = BytesIO()
	img.save(buffer, format="PNG")
	buffer.seek(0)
	
	return buffer


def temp_link_deleter(user_id):
	time.sleep(3600)
	delete_users_link(user_id)


def generate_secure_code(n):
    return ''.join(secrets.choice('0123456789') for _ in range(n))


def send_temp_photo(bot, chat_id, buffer, seconds=30, **kwargs):
	try:
		msg = bot.send_photo(chat_id, buffer, **kwargs)

		def delete():
			try:
				bot.delete_message(chat_id, msg.message_id)
			except Exception as e:
				logger.error(f"Ошибка удаления сообщения: {e}")

		threading.Timer(seconds, delete).start()
	except Exception as e:
		logger.error(f"Ошибка при отправке временного изображения: {e}")

def temp_link_deleter(temp_id, seconds=3600):
	try:
		def delete():
			try:
				delete_users_link(temp_id)
			except Exception as e:
				logger.error(f"Ошибка удаления сообщения: {e}")

		threading.Timer(seconds, delete).start()
	except Exception as e:
		logger.error(f"Ошибка при удалении временной ссылки: {e}")


def send_temp_message(bot, chat_id, text, seconds=30, **kwargs):
	try:
		msg = bot.send_message(chat_id, text, **kwargs)

		def delete():
			try:
				bot.delete_message(chat_id, msg.message_id)
			except Exception as e:
				logger.error(f"Ошибка удаления сообщения: {e}")

		threading.Timer(seconds, delete).start()
	except Exception as e:
		logger.error(f"Ошибка при отправке временного сообщения: {e}")
