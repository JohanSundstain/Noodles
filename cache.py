import time
import threading

class Cache:
    def __init__(self, ttl=100):
        self.ttl = ttl
        self.cache = {}
        self.expires = 0
        self.lock = threading.Lock()

    def get(self, key, loader=None):
        with self.lock:
            if key not in self.cache or time.time() >= self.expires:
                if loader is None:
                    return None

                loaded = loader()
                self.cache = loaded if isinstance(loaded, dict) else {}
                self.expires = time.time() + self.ttl

            return self.cache.get(key)

    def is_cached(self, key):
        with self.lock:
            return time.time() < self.expires and key in self.cache
    
    def invalidate(self):
        with self.lock:
            self.cache = {}
            self.expires = 0
		