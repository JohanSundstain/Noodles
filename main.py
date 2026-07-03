from fastapi import FastAPI, HTTPException
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
# CORE LOGIC
# ------------------------
def _to_str(user_id):
    return str(user_id)


def load_user_dict():
    result = subprocess.run(
        ['userlist'],
        capture_output=True,
        text=True,
        encoding='utf-8',
        timeout=10
    )

    users_list = re.findall(r'\d+\.\s+(\w+)', result.stdout or "")

    users_dict = {}
    for i, uid in enumerate(users_list, start=1):
        users_dict[uid] = i

    return users_dict


def get_user_index(user_id):
    return user_index_cache.get(str(user_id), load_user_dict)


def load_user_link(user_id):
    user_id_str = _to_str(user_id)

    user_index = user_index_cache.get(user_id_str, load_user_dict)

    if not user_index:
        logger.warning(f'User not found {user_id_str}')
        return None

    try:
        process = subprocess.Popen(
            ['sharelink'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )

        stdout, stderr = process.communicate(f'{user_index}\n', timeout=10)

        url = re.search(r'vless://[^\s]+', stdout or "")

        return url.group() if url else None

    except Exception as e:
        logger.error(f"sharelink error {user_id}: {e}")
        return None


# ------------------------
# API
# ------------------------

@app.post("/user/create")
def create_user(req: UserRequest):
    try:
        user_id = req.user_id

        # если уже есть — просто возвращаем ссылку
        if user_index_cache.is_cached(str(user_id)):
            link = load_user_link(user_id)
            return {"status": "exists", "link": link}

        result = subprocess.run(
            ['newuser'],
            input=str(user_id) + '\n',
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=10
        )

        url = re.search(r'vless://[^\s]+', result.stdout or "")

        if not url:
            logger.error(f"Failed to create user {user_id}: {result.stdout}")
            raise HTTPException(status_code=500, detail="User creation failed")

        return {
            "status": "ok",
            "link": url.group()
        }

    except Exception as e:
        logger.exception("create_user crashed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/user/{user_id}/exists")
def check_user(user_id: int):
    return {
        "exists": user_index_cache.is_cached(str(user_id))
    }


@app.get("/user/{user_id}/link")
def get_link(user_id: int):
    user_index = get_user_index(user_id)

    if not user_index:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        process = subprocess.Popen(
            ['sharelink'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )

        stdout, _ = process.communicate(f'{user_index}\n', timeout=10)

        url = re.search(r'vless://[^\s]+', stdout or "")

        if not url:
            raise HTTPException(status_code=500, detail="Link generation failed")

        return {
            "status": "ok",
            "link": url.group()
        }

    except Exception as e:
        logger.exception("get_link failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/user")
def delete_user(req: DeleteRequest):
    user_id = req.user_id

    user_index = get_user_index(user_id)

    if not user_index:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        process = subprocess.Popen(
            ['rmuser'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )

        stdout, stderr = process.communicate(f'{user_index}\n', timeout=10)

        if process.returncode != 0:
            logger.warning(f"rmuser error {user_id}: {stderr}")
            raise HTTPException(status_code=500, detail="rmuser failed")

        return {"status": "deleted"}

    except Exception as e:
        logger.exception("delete_user crashed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/user/schedule-delete")
def schedule_delete(req: ScheduleRequest):

    def delete():
        try:
            user_index = get_user_index(req.user_id)

            if user_index:
                subprocess.run(
                    ['rmuser'],
                    input=f"{user_index}\n",
                    text=True,
                    capture_output=True,
                    timeout=10
                )

        except Exception as e:
            logger.error(f"scheduled delete error: {e}")

    threading.Timer(req.seconds, delete).start()

    return {"status": "scheduled", "seconds": req.seconds}