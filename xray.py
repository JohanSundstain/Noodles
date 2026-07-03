import requests

import time
IP = "45.43.159.220:8000"


class APIClient:
    def __init__(self, ip):
        self.base_url = f"http://{ip}"
        self.session = requests.Session()

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
            print("CREATE:", data)
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
            print("DELETE:", data)
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
            print("EXISTS:", data)
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
            print("LINK:", data)
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
            print("SCHEDULE DELETE:", data)
            return data

        except Exception as e:
            print("SCHEDULE ERROR:", e)


# ------------------------
# TEST
# ------------------------
api = APIClient(IP)

api.create_user(12)
time.sleep(2)
api.user_exists(12)
time.sleep(2)
api.get_link(12)
api.delete_user(12)
api.schedule_delete(12, 60)