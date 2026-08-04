import json

from copy import deepcopy
from utils import get_user_list, restart_xray


from config import XRAY_CONF_PATH

def convert_tcp_to_xhttp(path: str = "/", mode: str = "auto") -> dict:

	with open(XRAY_CONF_PATH, "r", encoding="utf-8") as f:
		config = json.load(f)

	clients = get_user_list()

	new_clients = []
	for client in clients:
		new_client = {"email":client["email"], "id":client["id"]}
		new_clients.append(new_client)


	for inbound in config.get("inbounds", []):
		stream = inbound.get("streamSettings")

		if not stream:
			continue

		if stream.get("network") != "tcp":
			continue

		# меняем транспорт
		stream["network"] = "xhttp"

		# добавляем xhttp настройки
		stream["xhttpSettings"] = {
			"path": path,
			"mode": mode
		}

	with open(XRAY_CONF_PATH, "w", encoding="utf-8") as f:
		json.dump(config, f, indent=2, ensure_ascii=False)

	restart_xray()
	
