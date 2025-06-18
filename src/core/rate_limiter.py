import logging
from fastapi import Request, HTTPException, status
from src.core.redis_client import redis_client

logger = logging.getLogger(__name__)
REQUEST_LIMIT = 20 
TIME_WINDOW_SECONDS = 60 

async def manual_rate_limiter(request: Request):
    """
    A simple, manual rate limiter dependency using Redis.
    """
    if not redis_client:
        logger.warning("Redis client not available, skipping rate limit check.")
        return

    # Use the device ID, fall back to IP address.
    client_id = request.headers.get("x-device-id", request.client.host)
    
    # Create a unique key for this client in Redis
    redis_key = f"rate_limit:{client_id}"
    current_requests = 0

    try:
        # Use a pipeline for atomic operations
        pipeline = redis_client.pipeline()
        pipeline.incr(redis_key, 1)
        pipeline.expire(redis_key, TIME_WINDOW_SECONDS, nx=True) # Set expiration only if the key is new
        
        # Execute and get the current count
        results = pipeline.execute()
        current_requests = results[0]
            
    except Exception as e:
        logger.error(f"Could not check rate limit in Redis: {e}")

    if current_requests > REQUEST_LIMIT:
            logger.warning(f"Rate limit exceeded for client: {client_id}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {TIME_WINDOW_SECONDS} seconds."
            )