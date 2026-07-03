import time

class Cache:
	def __init__(self, ttl=100):
		self.ttl = ttl
		self.cache = {}
		self.expires = 0

	def get(self, key, loader=None):
		if key not in self.cache or time.time() >= self.expires:
			self.cache = loader()
			self.expires = time.time() + self.ttl
		return self.cache.get(key, None)

	def is_cached(self, key):
		return key in self.cache
	
	def invalidate(self):
		self.cache = {}
		self.expires = 0
		