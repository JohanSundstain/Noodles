from dataclasses import dataclass, field
from typing import List

from .client import APIServer
from config import API_TOKEN


class ServerInterface:
	def __init__(self):
		self._contries: List[APIServer] = [
			APIServer(id="fi-1",emoji="🇫🇮", ip="185.254.158.230:8000", type='raw', api_key=API_TOKEN), 
			APIServer(id="pl-1",emoji="🇵🇱", ip="45.43.137.116:8000", type='xhttp', api_key=API_TOKEN), 
			APIServer(id="de-1",emoji="🇩🇪", ip="185.245.35.242:8000", type='xhttp', api_key=API_TOKEN), 
			APIServer(id="hk-1",emoji="🇭🇰", ip="176.98.181.174:8000", type='raw', api_key=API_TOKEN), 
			APIServer(id="none",emoji="🏴‍☠️", ip="0.0.0.0:8000", type='none', api_key=API_TOKEN), 
		]


	def get_api_server(self, id: str) -> APIServer:
		return next(
			(api_server for api_server in self._contries if api_server.id == id),
			None)
	
	def get_all_api(self)->List[APIServer]:
		return self._contries

	def get_all_id(self) -> List[str]:
		return [api_server.id for api_server in self._contries if api_server.id != 'none']