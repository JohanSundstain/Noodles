import requests

IP = "45.43.159.220"

def create_user(user_id):
	response = requests.post(
    f"http://{IP}:8000/user/create",
    json={"user_id": user_id})

	data = response.json()

	print(data)

def delete_user(user_id):
	response = requests.delete(
    f"http://{IP}:8000/user",
    json={"user_id": user_id})

	data = response.json()

	print(data)

create_user(12)
