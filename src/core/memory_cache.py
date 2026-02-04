# src/core/memory_cache.py

import time
import logging
import threading
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)

class InMemoryCache:
    _instance = None

    MAX_SIZE = 10000
    
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
                time.sleep(60)
                try:
                    self.cleanup_expired()
                except Exception as e:
                    logger.error(f"Cache cleanup error: {e}")

        thread = threading.Thread(target=run_loop, daemon=True)
        thread.start()

    def cleanup_expired(self):
        now = time.time()
        keys_to_delete = []
        with self._lock:
            for key, expire_time in list(self._expirations.items()):
                if now > expire_time:
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                self._store.pop(key, None)
                self._expirations.pop(key, None)
        
        if keys_to_delete:
            logger.info(f"[MemoryCache] Cleaned up {len(keys_to_delete)} expired keys.")

    def _enforce_max_size(self):
        if len(self._store) >= self.MAX_SIZE:
            try:
                self._store.pop(next(iter(self._store)))
                logger.warning("[MemoryCache] Max size reached, evicted item.")
            except KeyError:
                pass

    def get(self, key: str):
        with self._lock:
            if key in self._expirations and time.time() > self._expirations[key]:
                del self._store[key]
                del self._expirations[key]
                return None
            
            val = self._store.get(key)
            if val:
                del self._store[key]
                self._store[key] = val
            return val

    def set(self, key: str, value: Any, ex: int = None):
        with self._lock:
            if key in self._store:
                del self._store[key]
            else:
                self._enforce_max_size()
            
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
            
            if key in self._store:
                del self._store[key]
            else:
                self._enforce_max_size()

            self._store[key] = str(new_val)
            return new_val

    def expire(self, key: str, time_seconds: int):
        with self._lock:
            if key not in self._store:
                return 0
            self._expirations[key] = time.time() + time_seconds
            return 1

# Singleton
memory_cache = InMemoryCache()