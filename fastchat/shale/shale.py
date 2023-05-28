
import argparse
import base64
import hashlib
import os
import redis

from datetime import datetime
from pydantic import BaseModel

from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from typing import Optional

from sqlalchemy import Table, Column, Integer, String, MetaData, create_engine, select

from sqlalchemy.orm import Session
from sqlalchemy.orm import declarative_base

Base = declarative_base()
mysql_url = 'mysql://root:mysql_password@mysql/shale'
engine = create_engine(mysql_url, echo=True)

def get_shale_secret():
    return os.environ["SHALE_ADMIN_SECRET"]

class UserApiKey(Base):
    __tablename__ = "user_api_key"

    user_id = Column(String(255), primary_key=True)
    user_email = Column(String(255))
    api_key = Column(String(255))


def init_mysql_tabels():
    print('init table')
    Base.metadata.create_all(engine)


def increase_redis_count(ak):
    r = redis.Redis(host="redis")
    if r.exists(ak):
        r.incr(ak)
    else:
        r.set(ak, 1)
        r.expire(ak, 60 * 60 * 24)

def get_redis_count(ak):
    r = redis.Redis(host="redis")
    if r.exists(ak):
        return int(r.get(ak))
    return 0
        
def check_ak(ak):
    stmt = select(UserApiKey).where(UserApiKey.api_key == ak)
    with Session(engine) as session:
        result = session.execute(stmt)
        return result.one_or_none() is not None

def create_ak(user_id, user_email):
    ak = 'SHALE-'+ base64.b64encode(hashlib.sha256((user_id + get_shale_secret() + datetime.now().strftime('$Y-%m-%d:%H:%M:%S.%f')).encode()).digest()).decode()
    with Session(engine) as session:
        session.merge(UserApiKey(api_key=ak, user_id=user_id, user_email=user_email))
        session.commit()
    return ak


class SecretRequest(BaseModel):
    secret: str
    user_id: str
    user_email: Optional[str] = None

class APIKeyChecker(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if "authorization" not in request.headers or not request.headers["authorization"].startswith('Bearer '):
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
            cnt = get_redis_count(ak)
            if cnt > 0 or check_ak(ak):
                increase_redis_count(ak)
                if cnt < int(os.environ.get("SHALE_AK_RATE_LIMIT", 1000)):
                    response = await call_next(request)
                else:
                    response = JSONResponse({"error": {
                        "code": 429,
                        "type": "limit_exceed",
                        "message": f"Rate limit of {ak} exceeded: {cnt+1}",
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="shaleprotocol.com"
    )
    parser.add_argument('subcommand')
    args = parser.parse_args()

    if args.subcommand == 'init_mysql':
        init_mysql_tabels()
    elif args.subcommand == 'create_ak':
        print(create_ak("shale", "shale@shaleprotocol.com"))
    elif args.subcommand == 'check_ak':
        print(check_ak("SHALE-Fb99b3vEhELzB9gvO8ASe2VYvp73jLCNN+zn+7yzrl0="))