import os
import secrets
import threading
from config import API_KEY
from fastapi import FastAPI, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel

from utils import (
	create_xray_user,
	create_link,
	get_client,
	delete_users,
	is_owner,
	is_admin,
	generate_secure_code
)

from logger import logger

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
			create_xray_user(user_id)
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
				logger.exception("create temp link crashed")
				return {"status" : "failed", "details": "create temp link crashed"}		
	else:
		return {"status": "faild", "details":"permision denied"}


@app.get("/user/{user_id}/exists")
def check_user(user_id: str, _=Security(verify_api_key)):
	client = get_client(user_id)
	return { "exists": client is not None}


@app.get("/user/{user_id}/link")
def get_link(user_id: str, _=Security(verify_api_key)):

	try:
		link = create_link(user_id)
		return { "status": "ok", "link": link}
	except HTTPException:
		raise
	except Exception as e:
		logger.exception("create user crashed")
		return {"status": "failed", "details": "create user crashed"}



@app.delete("/user")
def delete_user(req: UsersRequest, _=Security(verify_api_key)):
	user_ids = req.user_ids
	with write_lock:
		try:
			delete_users(user_ids)
			return {"status": "ok"}
		except HTTPException:
			raise
		except Exception as e:
			logger.exception("delete user crashed")
			return {"status": "failed", "details": "delete user crashed"}