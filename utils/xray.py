import os
import json
import requests
import uuid
import subprocess


from logger import logger



from urllib.parse import quote

#from config import (
#	XRAY_CONF_PATH,
#	SERVER_TYPE,
#	IP
#)
#from logger import logger

XRAY_CONF_PATH = "/usr/local/etc/xray/config.json"
IP = None
PBK = "nhel6cAx8AhDIn20wtm3hl2ALMqo_PgMPB5Y_1-23Gg"
ADMIN_ID = 1
OWNER_ID = 1
SERVER_NAME = 'kz'

def generate_secure_code(n : int) -> int:
	return ''.join(__import__('secrets').choice('0123456789') for _ in range(n))

def is_admin(user_id):
	return user_id == str(ADMIN_ID)

def is_owner(user_id):
	return user_id == str(OWNER_ID)

def get_user_list():
	with open(XRAY_CONF_PATH, "r", encoding="utf-8") as f:
		config = json.load(f)

	clients_list = config['inbounds'][0]['settings']['clients']

	return clients_list

def get_client(user_id, config=None):
	if config is None:
		with open(XRAY_CONF_PATH, "r", encoding="utf-8") as f:
			config = json.load(f)

	clients = config['inbounds'][0]['settings']['clients']
	for client in clients:
		if client['email'] == user_id:
			return client
	return None

def get_ip():
	global IP
	if IP is None:
		IP = requests.get("https://api.ipify.org").text
	return IP

def restart_xray():
    try:
        result = subprocess.run(
            ["systemctl", "restart", "xray"],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info("Xray успешно перезапущен")
        return True

    except subprocess.CalledProcessError as e:
        logger.error("Ошибка перезапуска Xray:")
        logger.error(e.stderr)
        return False


def create_user(user_id):
	with open(XRAY_CONF_PATH, "r", encoding="utf-8") as f:
			config = json.load(f)

	if get_client(user_id, config) is not None:
		return

	new_user = { "email": user_id, "id": str(uuid.uuid4()) }

	config["inbounds"][0]["settings"]["clients"].append(new_user)

	with open(XRAY_CONF_PATH, "w", encoding="utf-8") as f:
		json.dump(config, f, indent=2, ensure_ascii=False)

	restart_xray()


def delete_users(users):
	with open(XRAY_CONF_PATH, "r", encoding="utf-8") as f:
			config = json.load(f)

	clients = config['inbounds'][0]['settings']['clients']
	config['inbounds'][0]['settings']['clients'] = [
		client for client in config['inbounds'][0]['settings']['clients']
		if client['email'] not in users
	]

	with open(XRAY_CONF_PATH, "w", encoding="utf-8") as f:
		json.dump(config, f, indent=2, ensure_ascii=False)

	restart_xray()

	
def create_link(user_id):
	with open(XRAY_CONF_PATH, "r", encoding="utf-8") as f:
		config = json.load(f)
	
	client = get_client(user_id, config)
	if client is None:
		raise RuntimeError(f"Пользователь {user_id} не существует")
	uuid = client["ip"]
	ip = get_ip()
	path = config["inbounds"][0]["streamSettings"]["xhttpSettings"]["path"]
	encoded_path = quote(path, safe="")
	pbk = PBK
	sni = config["inbounds"][0]["streamSettings"]["realitySettings"]["serverNames"][0]
	sid = config["inbounds"][0]["streamSettings"]["realitySettings"]["shortIds"][0]
	mode = config["inbounds"][0]["streamSettings"]["xhttpSettings"]["mode"]
	srv_name = SERVER_NAME

	encoded_path = quote(path, safe="")
	base_url = (
		f"vless://{uuid}@{ip}:443"
		f"?type=xhttp"
		f"&security=reality"
		f"&pbk={pbk}"
		f'&fp=chrome'
		f"&sni={sni}"
		f"&sid={sid}"
		f"&path={encoded_path}"
		f"&mode={mode}"
		f"#{srv_name}")	
	
	return base_url
