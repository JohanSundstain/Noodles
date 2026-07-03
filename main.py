from fastapi import FastAPI
from pydantic import BaseModel
import re
import subprocess
import threading

from cache import Cache
from logger import logger

app = FastAPI()

user_index_cache = Cache(ttl=120)
# ------------------------
# MODELS
# ------------------------
class UserRequest(BaseModel):
    user_id: int


class DeleteRequest(BaseModel):
    user_id: int


class ScheduleRequest(BaseModel):
    user_id: int
    seconds: int = 3600

# ------------------------
# CORE LOGIC (ported)
# ------------------------
def _to_str(user_id):
    return str(user_id)


def load_user_dict():
    result = subprocess.run(
        ['userlist'],
        input='',
        capture_output=True,
        text=True,
        encoding='utf-8'
    )

    users_list = re.findall(r'\d+\.\s+(\w+)', result.stdout)

    users_dict = {}
    for i in range(len(users_list)):
        users_dict[users_list[i]] = i + 1

    return users_dict

def get_user_index(user_id):
    return user_index_cache.get(str(user_id), load_user_dict)

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

# ------------------------
# API ENDPOINTS
# ------------------------

@app.post("/user/create")
def create_user(req: UserRequest):
    user_id = req.user_id

    # уже существует
    if user_index_cache.is_cached(str(user_id)):
        return {
            "status": "exists",
            "link": load_user_link(user_id)
        }

    result = subprocess.run(
        ['newuser'],
        input=str(user_id) + '\n',
        capture_output=True,
        text=True,
        encoding='utf-8',
    )

    url = re.search(r'vless://[^\s]+', result.stdout)

    if not url:
        logger.error(f"Не удалось создать пользователя {user_id}")
        return {"status": "error"}

    return {
        "status": "ok",
        "link": url.group()
    }


@app.get("/user/{user_id}/exists")
def check_user(user_id: int):
    return {
        "exists": user_index_cache.is_cached(str(user_id))
    }


@app.get("/user/{user_id}/link")
def get_link(user_id: int):
    user_index = get_user_index(user_id)

    if user_index is None:
        return {"status": "not_found"}

    process = subprocess.Popen(
        ['sharelink'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
    )

    stdout, _ = process.communicate(f'{user_index}\n')

    url = re.search(r'vless://[^\s]+', stdout)

    if not url:
        return {"status": "error"}

    return {
        "status": "ok",
        "link": url.group()
    }


@app.delete("/user")
def delete_user(req: DeleteRequest):
    user_id = req.user_id

    user_index = get_user_index(user_id)

    if user_index is None:
        return {"status": "not_found"}

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
        logger.warning(f"rmuser error {user_id}: {stderr}")
        return {"status": "error"}

    return {"status": "deleted"}


@app.post("/user/schedule-delete")
def schedule_delete(req: ScheduleRequest):
    def delete():
        try:
            user_index = get_user_index(req.user_id)
            if user_index:
                subprocess.Popen(
                    ['rmuser'],
                    stdin=subprocess.PIPE,
                    text=True
                ).communicate(f"{user_index}\n")
        except Exception as e:
            logger.error(f"scheduled delete error: {e}")

    threading.Timer(req.seconds, delete).start()

    return {"status": "scheduled", "seconds": req.seconds}