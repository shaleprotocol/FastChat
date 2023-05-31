import argparse
import base64
import hashlib
import os
import asyncio
import uuid
from datetime import datetime
from typing import Optional

import redis
from pydantic import BaseModel
from sqlalchemy import (Column, DateTime, Integer, String, Text, Time, Uuid,
                        create_engine, select)
from sqlalchemy.orm import Session, declarative_base
from sqlalchemy.sql import func
from starlette.middleware.base import (BaseHTTPMiddleware,
                                       RequestResponseEndpoint)
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import Message

Base = declarative_base()
mysql_url = 'mysql://root:mysql_password@mysql/shale'
engine = create_engine(mysql_url, echo=True)

default_api_limit = int(os.environ.get("SHALE_AK_RATE_LIMIT", 1000))

def get_shale_secret():
    return os.environ["SHALE_ADMIN_SECRET"]

class UserApiKey(Base):
    __tablename__ = "user_api_key"

    user_id = Column(String(255), primary_key=True)
    user_email = Column(String(255))
    api_key = Column(String(255))


class RequestLog(Base):
    __tablename__ = "request_log"

    request_id = Column(Uuid, primary_key=True)
    api_key = Column(String(255))
    method = Column(String(20))
    url = Column(String(100))
    client_host = Column(String(20))
    client_port = Column(Integer)
    headers = Column(Text)
    request_body = Column(Text)
    response_body = Column(Text)
    duration = Column(Time)
    time_created = Column(DateTime(timezone=False), server_default=func.now())
    time_updated = Column(DateTime(timezone=False), onupdate=func.now())


def init_mysql_tabels():
    print('init table')
    Base.metadata.create_all(engine)


def get_redis_count(ak):
    r = redis.Redis(host="redis")
    v = r.get(ak)
    if v is None:
        return 0
    return v


def check_ak(ak):
    stmt = select(UserApiKey).where(UserApiKey.api_key == ak)
    with Session(engine) as session:
        result = session.execute(stmt)
        return result.one_or_none() is not None


def create_ak(user_id, user_email):
    ak = 'shale-' + \
        base64.b64encode(hashlib.sha256(
            (user_id + get_shale_secret()).encode()).digest()).decode()
    ak = ak[:20]
    with Session(engine) as session:
        session.merge(UserApiKey(
            api_key=ak, user_id=user_id, user_email=user_email))
        session.commit()
    return ak


async def log_request_to_db(request, req_body):
    request_id = uuid.uuid4()

    ak = ''
    if 'authorization' in request.headers and request.headers['authorization'].startswith('Bearer '):
        ak = request.headers['authorization'].split()[1]

    with Session(engine) as session:
        log_entry = RequestLog(
            request_id=request_id,
            api_key=ak,
            method=request.method,
            url=request.url,
            headers=str(request.headers),
            client_host=request.client.host,
            client_port=request.client.port,
            request_body=req_body.decode())
        session.merge(log_entry)
        session.commit()


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
                    "message": f"Forever FREE! Sign-up at https://shaleprotocol.com",
                    "param": ""
                }}, status_code=401)
        else:
            ak = request.headers["authorization"].split()[1]
            r = redis.Redis(host="redis")
            if not r.exists(ak):
                if not check_ak(ak):
                    response = JSONResponse({"error": {
                        "code": 401,
                        "type": "invalid_ak",
                        "message": f"Forever FREE! Sign-up at https://shaleprotocol.com",
                        "param": ""

                    }}, status_code=401)
                else:
                    # Init entry in Redis.
                    r.set(ak, default_api_limit - 1)
                    r.expire(ak, 60 * 60 * 24)
                    response = await call_next(request)
            else:
                remaind = r.decr(ak)
                if remaind >= 0:
                    response = await call_next(request)
                else:
                    response = JSONResponse({"error": {
                        "code": 429,
                        "type": "limit_exceed",
                        "message": f"Quota of {ak} is reached. Contact us at https://shaleprotocol.com to increase.",
                        "param": ""

                    }}, status_code=429)
        return response


class RequestLogger(BaseHTTPMiddleware):

    async def set_body(self, request: Request, body: bytes):
        async def receive() -> Message:
            return {'type': 'http.request', 'body': body}
        request._receive = receive

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        req_body = await request.body()
        await self.set_body(request, req_body)
        response = await call_next(request)
        asyncio.create_task(log_request_to_db(request, req_body))
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
        print(check_ak("shale-lHH0EZBAZGzMS1"))
