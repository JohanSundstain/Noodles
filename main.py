import threading
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from logger import logger
# Импортируем все необходимые функции, включая get_user_index
from xray import (
    get_user_index,
    create_external_user,
    load_user_link,
    remove_external_user,
    user_index_cache  # Импортируем объект кэша для возможности его очистки
)

app = FastAPI()

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
# API
# ------------------------

@app.post("/user/create")
def create_user(req: UserRequest):
    try:
        user_id = req.user_id

        # Если пользователь уже существует в системе — возвращаем его ссылку
        if get_user_index(user_id):
            link = load_user_link(user_id)
            return {"status": "exists", "link": link}

        # Создаем нового пользователя
        url = create_external_user(user_id)

        if not url:
            raise HTTPException(status_code=500, detail="User creation failed")

        # Принудительно очищаем кэш, чтобы при следующем запросе userlist обновился
        user_index_cache.invalidate() 
        
        return {
            "status": "ok",
            "link": url
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("create_user crashed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/user/{user_id}/exists")
def check_user(user_id: int):
    # Корректная проверка существования пользователя через вызов индекса
    index = get_user_index(user_id)
    return {
        "exists": index is not None
    }


@app.get("/user/{user_id}/link")
def get_link(user_id: int):
    # Сначала проверяем, есть ли вообще такой пользователь
    if not get_user_index(user_id):
        raise HTTPException(status_code=404, detail="User not found")

    # load_user_link сама внутри себя получит индекс по user_id
    link = load_user_link(user_id)
    if not link:
        raise HTTPException(status_code=500, detail="Link generation failed")

    return {
        "status": "ok",
        "link": link
    }


@app.delete("/user")
def delete_user(req: DeleteRequest):
    user_id = req.user_id

    user_index = get_user_index(user_id)
    if not user_index:
        raise HTTPException(status_code=404, detail="User not found")

    if not remove_external_user(user_index):
        raise HTTPException(status_code=500, detail="rmuser failed")

    # Сбрасываем кэш после удаления, чтобы данные обновились
    user_index_cache.invalidate()
    return {"status": "deleted"}


@app.post("/user/schedule-delete")
def schedule_delete(req: ScheduleRequest):

    def delete():
        try:
            user_index = get_user_index(req.user_id)
            if user_index:
                if remove_external_user(user_index):
                    user_index_cache.invalidate()
        except Exception as e:
            logger.error(f"scheduled delete error: {e}")

    threading.Timer(req.seconds, delete).start()

    return {"status": "scheduled", "seconds": req.seconds}