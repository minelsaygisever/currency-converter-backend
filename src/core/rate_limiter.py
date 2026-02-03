import logging
from fastapi import Request, HTTPException, status
from src.core.memory_cache import memory_cache

logger = logging.getLogger(__name__)
REQUEST_LIMIT = 20 
TIME_WINDOW_SECONDS = 60 

async def manual_rate_limiter(request: Request):
    """
    In-Memory Rate Limiter.
    """
    client_id = request.headers.get("x-device-id", request.client.host)
    cache_key = f"rate_limit:{client_id}"
    
    current_requests = 0

    try:
        current_requests = memory_cache.incr(cache_key, 1)
        
        if current_requests == 1:
            memory_cache.expire(cache_key, TIME_WINDOW_SECONDS)
            
    except Exception as e:
        logger.error(f"Could not check rate limit: {e}")
        return

    if current_requests > REQUEST_LIMIT:
            logger.warning(f"Rate limit exceeded for client: {client_id}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {TIME_WINDOW_SECONDS} seconds."
            )