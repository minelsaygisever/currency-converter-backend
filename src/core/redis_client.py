import logging
import redis
from src.core.config import settings

logger = logging.getLogger(__name__)
class RedisManager:
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_client(self):
        if self._client is None:
            try:
                logger.debug("--- REDIS CLIENT INITIALIZATION STARTED ---")
                logger.debug(f"Attempting to connect to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
                
                self._client = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    db=0,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_keepalive=True,
                    retry_on_timeout=False,
                    ssl=True,  
                    ssl_cert_reqs=None
                )

                logger.debug("Testing connection with INFO command...")
                info = self._client.info()
                logger.info(f"Successfully connected to Redis. Server version: {info.get('redis_version', 'unknown')}")
                
            except Exception as e:
                logger.error("--- FAILED TO INITIALIZE REDIS CLIENT ---")
                logger.error(f"An unexpected error of type {type(e).__name__} occurred: {e}", exc_info=True)
                self._client = None
                
        return self._client

redis_manager = RedisManager()

def get_redis_client():
    return redis_manager.get_client()