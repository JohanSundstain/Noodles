import subprocess
import secrets
import time
import re
import qrcode
from io import BytesIO

def create_user(user_id):
	user_id_str = str(user_id)
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
