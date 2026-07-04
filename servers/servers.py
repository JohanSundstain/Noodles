from dataclasses import dataclass, field
from typing import Dict, List

from .client import APIClient
from config import API_TOKEN

@dataclass
class CountryConfig:
	name: str
	emoji: str
	servers: List[APIClient]


class ServerInterface:
	def __init__(self):
		self._contries: Dict[str, CountryConfig] = {
		"FI": CountryConfig(
			name="Финляндия",
			emoji="🇫🇮",
			servers=[
				APIClient(id="fi-1", ip="45.43.159.220:8000", api_key=API_TOKEN), # ПОМЕНЯЙ СУКА ПОТОМ ТОЛЬКО, А ТО ОПЯТЬ ЗАБУДЕШЬ Е6ЛАН
			]
		),
		"HK": CountryConfig(
			name="Гонконг",
			emoji="🇭🇰",
			servers=[
				APIClient(id="hk-1", ip="1.1.1.1:8000", api_key=API_TOKEN), # ПОМЕНЯЙ СУКА ПОТОМ ТОЛЬКО, А ТО ОПЯТЬ ЗАБУДЕШЬ Е6ЛАН
			]
		),
		"UNKNOWN": CountryConfig(
			name="Локация не выбрана",
			emoji="🏴‍☠️",
			servers=[
				APIClient(id="none", ip="0.0.0.0:8000", api_key=API_TOKEN), # ПОМЕНЯЙ СУКА ПОТОМ ТОЛЬКО, А ТО ОПЯТЬ ЗАБУДЕШЬ Е6ЛАН
			]
		)
	}
	
	def get_country_ids(self, country:str)-> list[str]:
		return [server.id for server in self._contries[country].servers] 

	def get_api_server(self, id: str) -> APIClient:
		return next((server for config in self._contries.values() for server in config.servers if server.id == id), None)
	
	def get_contries(self)->Dict[str, CountryConfig]:
		return self._contries

	def get_country_by_server_id(self, server_id: str) -> CountryConfig | None:
		return next(
			(cfg for cfg in self._contries.values()
			for server in cfg.servers
			if server.id == server_id),
			None
		)