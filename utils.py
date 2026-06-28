import subprocess
import time
import re
import qrcode
from io import BytesIO

def create_user(user_id):
	# Передаем ввод через параметр input
	result = subprocess.run(
		['newuser'],  # или ['/path/to/program']
		input=f'{user_id}\n',
		capture_output=True,
		text=True,
		encoding='utf-8'
	)

	url = re.search(r'vless://[^\s]+', result.stdout)
	if url:
		return url.group()


def get_user_list():
	process = subprocess.Popen(
		['rmuser'],
		stdin=subprocess.PIPE,
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE,
		text=True,
		encoding='utf-8'
	)
	
	stdout, _ = process.communicate()
	
	users = re.findall(r'\d+\.\s+(\w+)', stdout)
	return users

def check_user(user_id):
	users = get_user_list()
	
	return user_id in users


def delete_user_by_name(username):
	"""Удаляет пользователя по имени"""
	users = get_user_list()
	
	if username not in users:
		print(f"Пользователь {username} не найден")
		return
	
	# Находим номер пользователя
	user_number = users.index(username) + 1
	
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


def get_users_link(username):
	users = get_user_list()

	if username not in users:
		print(f"Пользователь {username} не найден")
		return
	
	user_number = users.index(username) + 1

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
	delete_user_by_name(user_id)