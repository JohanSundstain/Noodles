from dataclasses import dataclass, field
from typing import Dict, List

from client import APIClient
from config import API_TOKEN

@dataclass
class CountryConfig:
    name: str
    emoji: str
    servers: List[APIClient]

COUNTRIES: Dict[str, CountryConfig] = {
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
        name="Не выбрано",
        emoji="🇭🇰",
        servers=[
            APIClient(id="none", ip="0.0.0.0:8000", api_key=API_TOKEN), # ПОМЕНЯЙ СУКА ПОТОМ ТОЛЬКО, А ТО ОПЯТЬ ЗАБУДЕШЬ Е6ЛАН
		]
    )
}

def get_country_ids(country):
    return [server.id for server in COUNTRIES[country].servers]
        
def get_api_server(id):
    return next((server for config in COUNTRIES.values() for server in config.servers if server.id == id), None)