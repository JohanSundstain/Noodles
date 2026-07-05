from .cache import Cache

user_index_cache = Cache(ttl=100)

__all__ = [
	'user_index_cache'
]