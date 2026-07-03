import time
import requests

from config import API_KEY

IP = "45.43.159.220:8000"

class APIClient:
    def __init__(self, ip, api_key):
        self.base_url = f"http://{ip}"
        self.session = requests.Session()
        
        # Добавляем заголовок авторизации один раз. 
        # Теперь requests будет автоматически слать его с каждым запросом.
        self.session.headers.update({"X-API-Key": api_key})

    # ------------------------
    # CREATE USER
    # ------------------------
    def create_user(self, user_id: int):
        try:
            response = self.session.post(
                f"{self.base_url}/user/create",
                json={"user_id": user_id},
                timeout=10
            )

            data = response.json()
            print(f"CREATE [{response.status_code}]:", data)
            return data

        except Exception as e:
            print("CREATE ERROR:", e)

    # ------------------------
    # DELETE USER
    # ------------------------
    def delete_user(self, user_id: int):
        try:
            response = self.session.delete(
                f"{self.base_url}/user",
                json={"user_id": user_id},
                timeout=10
            )

            data = response.json()
            print(f"DELETE [{response.status_code}]:", data)
            return data

        except Exception as e:
            print("DELETE ERROR:", e)

    # ------------------------
    # CHECK USER EXISTS
    # ------------------------
    def user_exists(self, user_id: int):
        try:
            response = self.session.get(
                f"{self.base_url}/user/{user_id}/exists",
                timeout=10
            )

            data = response.json()
            print(f"EXISTS [{response.status_code}]:", data)
            return data

        except Exception as e:
            print("EXISTS ERROR:", e)

    # ------------------------
    # GET USER LINK
    # ------------------------
    def get_link(self, user_id: int):
        try:
            response = self.session.get(
                f"{self.base_url}/user/{user_id}/link",
                timeout=10
            )

            data = response.json()
            print(f"LINK [{response.status_code}]:", data)
            return data

        except Exception as e:
            print("LINK ERROR:", e)

    # ------------------------
    # SCHEDULE DELETE
    # ------------------------
    def schedule_delete(self, user_id: int, seconds: int = 3600):
        try:
            response = self.session.post(
                f"{self.base_url}/user/schedule-delete",
                json={
                    "user_id": user_id,
                    "seconds": seconds
                },
                timeout=10
            )

            data = response.json()
            print(f"SCHEDULE DELETE [{response.status_code}]:", data)
            return data

        except Exception as e:
            print("SCHEDULE ERROR:", e)


# ------------------------
# TEST
# ------------------------
# Передаем IP сервера и наш секретный API-ключ
api = APIClient(IP, API_KEY)

print("--- Тест 1: Создание пользователя ---")
api.create_user(12)
time.sleep(1)

print("\n--- Тест 2: Проверка существования ---")
api.user_exists(12)
time.sleep(1)

print("\n--- Тест 3: Получение ссылки ---")
api.get_link(12)
time.sleep(1)

print("\n--- Тест 4: Немедленное удаление ---")
api.delete_user(12)
time.sleep(1)

print("\n--- Тест 5: Планирование удаления для НОВОГО пользователя ---")
api.create_user(99)             # Создаем другого пользователя под отложенное удаление
api.schedule_delete(99, 10)     # Планируем удаление через 10 секунд

print("Ждем 12 секунд, пока сработает таймер на сервере...")
time.sleep(12)

print("\n--- Тест 6: Проверка, удалился ли пользователь 99 по таймеру ---")
api.user_exists(99)             # Должно вернуть {"exists": false}