import re
import subprocess
import threading
from logger import logger


def _to_str(user_id):
    return str(user_id)


def create_user(user_id):
    user_id_str = _to_str(user_id)

    if check_user(user_id):
        return get_users_link(user_id)

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


def get_user_list():
    result = subprocess.run(
        ['userlist'],
        input='',
        capture_output=True,
        text=True,
        encoding='utf-8',
    )

    users = re.findall(r'\d+\.\s+(\w+)', result.stdout)
    return users


def check_user(user_id):
    user_id_str = _to_str(user_id)
    return user_id_str in get_user_list()


def delete_users_link(user_id):
    user_id_str = _to_str(user_id)
    users = get_user_list()

    if user_id_str not in users:
        logger.warning(f'Пользователь {user_id_str} не найден при попытке удаления')
        return

    user_number = users.index(user_id_str) + 1
    process = subprocess.Popen(
        ['rmuser'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
    )

    stdout, stderr = process.communicate(f'{user_number}\n')
    if process.returncode != 0:
        logger.warning(f'Ошибка rmuser для {user_id_str}: {stderr.strip()}')


def get_users_link(user_id):
    user_id_str = _to_str(user_id)
    users = get_user_list()

    if user_id_str not in users:
        logger.warning(f'Пользователь {user_id_str} не найден при получении ссылки')
        return None

    user_number = users.index(user_id_str) + 1
    process = subprocess.Popen(
        ['sharelink'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
    )

    stdout, stderr = process.communicate(f'{user_number}\n')
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
