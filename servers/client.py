import time
import requests
from utils import logger

from config import API_TOKEN

class APIClient:
	def __init__(self, id, ip, api_key):
		self.ip = ip
		self.id = id
		self.base_url = f"http://{ip}"
		self.session = requests.Session()
		
		# Добавляем заголовок авторизации один раз. 
		# Теперь requests будет автоматически слать его с каждым запросом.
		self.session.headers.update({"X-API-Key": api_key})

	# ------------------------
	# CREATE USER
	# ------------------------
	def create_user(self, user_id: str):
		try:
			response = self.session.post(
				f"{self.base_url}/user/create",
				json={"user_id": user_id},
				timeout=10
			)

			data = response.json()
			logger.info(f"CREATE [{response.status_code}]:{data}")
			return data

		except Exception as e:
			logger.error(f"CREATE ERROR: {e}")

	# ------------------------
	# DELETE USER
	# ------------------------
	def delete_user(self, user_ids: list[str]):
		try:
			response = self.session.delete(
				f"{self.base_url}/user",
				json={"user_ids": user_ids},
				timeout=10
			)

			data = response.json()
			logger.info(f"DELETE [{response.status_code}]: {data}")
			return data

		except Exception as e:
			logger.error(f"DELETE ERROR: {e}")


	def delete_users(self, user_ids: list[int]):
		try:
			response = self.session.delete(
				f"{self.base_url}/user",
				json={"user_ids": user_ids},
				timeout=10
			)

			data = response.json()
			logger.info(f"DELETE [{response.status_code}]: {data}")
			return data

		except Exception as e:
			logger.error(f"DELETE ERROR: {e}")

	# ------------------------
	# CHECK USER EXISTS
	# ------------------------
	def user_exists(self, user_id: str):
		try:
			response = self.session.get(
				f"{self.base_url}/user/{user_id}/exists",
				timeout=10
			)

			data = response.json()
			logger.info(f"EXISTS [{response.status_code}]: {data}")
			return data

		except Exception as e:
			logger.error(f"EXISTS ERROR:", e)

	# ------------------------
	# GET USER LINK
	# ------------------------
	def get_link(self, user_id: str):
		try:
			response = self.session.get(
				f"{self.base_url}/user/{user_id}/link",
				timeout=10
			)

			data = response.json()
			logger.info(f"LINK [{response.status_code}]: {data}")
			return data

		except Exception as e:
			logger.error(f"LINK ERROR: {e}")

	# ------------------------
	# GET TEMP LINK
	# ------------------------
	def get_temp_link(self, user_id: str, seconds: int = 3600):
		try:
			response = self.session.post(
				f"{self.base_url}/user/temp_link",
				json={
					"user_id": user_id,
					"seconds": seconds
				},
				timeout=10
			)

			data = response.json()
			logger.info(f"TEMP LINK [{response.status_code}]: {data}")
			return data

		except Exception as e:
			logger.error(f"TEMP LINK ERROR: {e}")


	def ip(self):
		return self.ip

	def id(self):
		return self.id
