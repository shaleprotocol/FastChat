import os
import redis

from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

def check_redis_count(ak):
    r = redis.Redis()
    cnt = 0
    if r.exists(ak):
        cnt = int(r.get(ak))
    cnt += 1
    r.set(ak, cnt)
    return cnt
        
def check_ak(ak):
    return True

class APIKeyChecker(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        ak = request.headers["authorization"].split()[1]
        if check_ak(ak):
            cnt = check_redis_count(ak)
            if cnt <= os.environ.get("SHALE_AK_RATE_LIMIT", 1):
                response = await call_next(request)
            else:
                print(ak, cnt)
                response = JSONResponse({"error": {
                    f"Rate limit of {ak} exceeded: {cnt}"}
                }, status_code=429)
        else:
            print(ak)
            response = JSONResponse({"error": f"Invalid API_KEY {ak}"}, status_code=429)
        return response