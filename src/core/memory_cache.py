import time
import logging
import threading
from threading import Lock

logger = logging.getLogger(__name__)

class InMemoryCache:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._store = {}
            cls._instance._expirations = {}
            cls._instance._lock = Lock()
            cls._instance._start_cleanup_loop()
        return cls._instance
    
    def _start_cleanup_loop(self):
        def run_loop():
            while True:
                time.sleep(600)  # 10 minutes
                self.cleanup_expired()

        thread = threading.Thread(target=run_loop, daemon=True)
        thread.start()

    def cleanup_expired(self):
        now = time.time()
        keys_to_delete = []

        with self._lock:
            for key, expire_time in self._expirations.items():
                if now > expire_time:
                    keys_to_delete.append(key)
            
            count = 0
            for key in keys_to_delete:
                if key in self._store:
                    del self._store[key]
                if key in self._expirations:
                    del self._expirations[key]
                count += 1
        
        if count > 0:
            logger.info(f"[MemoryCache] Cleaned up {count} expired keys.")

    def get(self, key: str):
        with self._lock:
            if key in self._expirations and time.time() > self._expirations[key]:
                self.delete(key)
                return None
            return self._store.get(key)

    def set(self, key: str, value: str, ex: int = None):
        with self._lock:
            self._store[key] = value
            if ex:
                self._expirations[key] = time.time() + ex
            elif key in self._expirations:
                del self._expirations[key]
            return True

    def delete(self, key: str):
        with self._lock:
            deleted = 0
            if key in self._store:
                del self._store[key]
                deleted = 1
            if key in self._expirations:
                del self._expirations[key]
            return deleted

    def incr(self, key: str, amount: int = 1):
        with self._lock:
            if key in self._expirations and time.time() > self._expirations[key]:
                if key in self._store: del self._store[key]
                del self._expirations[key]

            current = int(self._store.get(key, 0))
            new_val = current + amount
            self._store[key] = str(new_val)
            return new_val

    def expire(self, key: str, time_seconds: int):
        with self._lock:
            if key not in self._store:
                return 0
            self._expirations[key] = time.time() + time_seconds
            return 1
            
memory_cache = InMemoryCache()