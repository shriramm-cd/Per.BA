import time
from fastapi import Request, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from backend.config import settings
from backend.shared.logger import get_logger

logger = get_logger(__name__)

# Define Header Key lookup
API_KEY_HEADER = APIKeyHeader(name="X-API-KEY", auto_error=False)

async def verify_api_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    """
    FastAPI dependency injection checking key validity.
    """
    if not api_key or api_key != settings.API_KEY:
        raise HTTPException(
            status_code=403, 
            detail="Forbidden. Access token invalid or missing from X-API-KEY header."
        )
    return api_key

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Structured middleware logging execution times and status codes.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        
        # Capture query params and paths
        path = request.url.path
        method = request.method
        
        logger.info(f"Incoming Request: {method} {path}")
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            logger.info(
                f"Completed Request: {method} {path} - Status: {response.status_code}", 
                extra={
                    "status_code": response.status_code,
                    "process_time_ms": round(process_time * 1000, 2)
                }
            )
            return response
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Failed Request: {method} {path} - Error: {str(e)}",
                extra={
                    "process_time_ms": round(process_time * 1000, 2)
                }
            )
            raise e

# INTEGRATION NOTE
# Verify security header X-API-KEY.
# Add RequestLoggingMiddleware to FastAPI app instance inside main.py.
