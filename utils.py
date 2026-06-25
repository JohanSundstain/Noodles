import subprocess
import re

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


def delete_user_by_name(username):
    """Удаляет пользователя по имени"""
    users = get_user_list()
    print(f"Найдены пользователи: {users}")
    
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
