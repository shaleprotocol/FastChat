import os
import redis

from pydantic import BaseModel

from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from typing import Optional

def check_redis_count(ak):
    r = redis.Redis()
    cnt = 0
    if r.exists(ak):
        cnt = int(r.get(ak))
    cnt += 1
    r.set(ak, cnt)
    return cnt
        
def check_ak(ak):
    return ak != 'INVALID'

def create_ak(user_id, user_name):
    return 'random'

class SecretRequest(BaseModel):
    secret: str
    user_id: Optional[str] = None
    user_email: Optional[str] = None

class APIKeyChecker(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if "authorization" not in request.headers or request.headers["authorization"].startswith('Bearer '):
            if request.url.path == "/v1/shale_create_api_key":
                response = await call_next(request)
            else:
                response = JSONResponse({"error": {
                    "code": 401,
                    "type": "no_ak",
                    "message": f"API_KEY should be provided",
                    "param": ""
                }}, status_code=401)
        else:
            ak = request.headers["authorization"].split()[1]
            if check_ak(ak):
                cnt = check_redis_count(ak)
                if cnt <= os.environ.get("SHALE_AK_RATE_LIMIT", 1000):
                    response = await call_next(request)
                else:
                    response = JSONResponse({"error": {
                        "code": 429,
                        "type": "limit_exceed",
                        "message": f"Rate limit of {ak} exceeded: {cnt}",
                        "param": ""

                    }}, status_code=429)
            else:
                response = JSONResponse({"error": {
                    "code": 401,
                    "type": "invalid_ak",
                    "message": f"Invalid API_KEY: {ak}",
                    "param": ""

                }}, status_code=401)
        return response