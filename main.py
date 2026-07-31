import os
import secrets
import threading
from config import API_KEY
from fastapi import FastAPI, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel

from utils import (
	create_user,
	create_link,
	get_client,
	delete_users,
	is_owner,
	is_admin,
	generate_secure_code
)

from logger import logger
from cache import user_index_cache

app = FastAPI()

# Глобальный лок для синхронизации создания/удаления пользователей
write_lock = threading.Lock()

# Глобальный  словарь  временных индексов для ссылок
temp_links = {} # temp_id : 

# ------------------------
# AUTHENTICATION CONFIG
# ------------------------
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def verify_api_key(api_key: str = Security(api_key_header)):
	"""Зависимость для проверки валидности API-ключа."""
	if not api_key:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="API Key is missing"
		)
	
	# Безопасное сравнение строк против Timing Attack
	if not secrets.compare_digest(api_key, API_KEY):
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail="Invalid API Key"
		)
	return api_key


# ------------------------
# MODELS
# ------------------------
class UserRequest(BaseModel):
	user_id: str


class DeleteRequest(BaseModel):
	user_id: str


class ScheduleRequest(BaseModel):
	user_id: str
	seconds: int = 3600


class UsersRequest(BaseModel):
	user_ids: list[str]

# ------------------------
# API (Защищенные эндпоинты)
# ------------------------

@app.post("/user/create")
def create_user(req: UserRequest, _=Security(verify_api_key)):
	user_id = req.user_id

	with write_lock:
		try:
			create_user(user_id)
			return {"status": "ok",}			
		except HTTPException:
			raise
		except Exception as e:
			logger.exception("create_user crashed")
			raise HTTPException(status_code=500, detail=str(e))


@app.post("/user/temp_link")
def get_temp_link(req: ScheduleRequest, _=Security(verify_api_key)):
	user_id = req.user_id

	if is_admin(user_id) or is_owner(user_id):
		with write_lock:
			try:
				temp_name = 'temp'+generate_secure_code(8)
				create_user(temp_name)	
				url = create_link(temp_name)
				def delete():
					with write_lock:
						try:
							delete_users([temp_name])
						except Exception as e:
							logger.error(f"scheduled delete error: {e}")

				threading.Timer(req.seconds, delete).start()

				return {"status" : "ok", "link": url}				
			except HTTPException:
				raise
			except Exception as e:
				logger.exception("create_user crashed")
				raise HTTPException(status_code=500, detail=str(e))
	else:
		return {"status": "faild", "details":"permision denied"}


@app.get("/user/{user_id}/exists")
def check_user(user_id: int, _=Security(verify_api_key)):
	index = get_user_index(user_id)
	return { "exists": index is not None}


@app.get("/user/{user_id}/link")
def get_link(user_id: int, _=Security(verify_api_key)):
		
	link = load_user_link(user_id)
	if not link:
		return { "status": "failed", "details":"load_user_link() failed"}
	else:
		return { "status": "ok", "link": link}


@app.delete("/user")
def delete_user(req: DeleteRequest, _=Security(verify_api_key)):
	user_id = req.user_id

	with write_lock:
		try:
			user_index = get_user_index(user_id)
			if not user_index:
				return {"status": "failed", "details": "User not found"}

			if not remove_external_user(user_index):
				return {"status": "failed", "details": "rmuser failed"}

			user_index_cache.invalidate()
			return {"status": "ok"}
			
		except HTTPException:
			raise
		except Exception as e:
			logger.exception("delete_user crashed")
			raise HTTPException(status_code=500, detail=str(e))


@app.delete("/users")
def delete_several_user(req: UsersRequest, _=Security(verify_api_key)):
	user_ids = req.user_ids
	deleted = []
	failed = []
	not_found = []
	with write_lock:
		try:
			for user_id in user_ids:
				user_index = get_user_index(user_id)
				if user_index:
					if remove_external_user(user_index):
						deleted.append(user_id)
						user_index_cache.invalidate()
					else:
						failed.append(user_id)
				else:
					not_found.append(user_id)

			
			return {"deleted": deleted, "failed" : failed, "not_found": not_found}
			
		except HTTPException:
			raise
		except Exception as e:
			logger.exception("delete_user crashed")
			raise HTTPException(status_code=500, detail=str(e))


@app.post("/user/schedule-delete")
def schedule_delete(req: ScheduleRequest, _=Security(verify_api_key)):
	def delete():
		with write_lock:
			try:
				user_index = get_user_index(req.user_id)
				if user_index:
					if remove_external_user(user_index):
						user_index_cache.invalidate()
			except Exception as e:
				logger.error(f"scheduled delete error: {e}")

	threading.Timer(req.seconds, delete).start()

	return {"status": "scheduled", "seconds": req.seconds}