from pydantic import BaseModel

class ErrorDetail(BaseModel):
    """
    A standard response body for HTTP exceptions.
    Compatible with FastAPI's default HTTPException format {"detail": "..."}
    """
    detail: str