import base64
import hashlib
import json
import logging
from http.cookies import SimpleCookie

from redis import asyncio as redis_async

from app.core.config import settings
from app.core.security import decode_token


logger = logging.getLogger("meritforge.middleware")


class IdempotencyMiddleware:
    def __init__(self, app, redis_url: str, ttl_seconds: int = 86400):
        self.app = app
        self.redis = redis_async.from_url(redis_url, decode_responses=True)
        self.ttl_seconds = ttl_seconds

    @staticmethod
    def _header_value(scope: dict, name: bytes) -> str | None:
        target = name.lower()
        for header_name, header_value in scope.get("headers", []):
            if header_name.lower() == target:
                return header_value.decode("latin-1")
        return None

    @staticmethod
    def _request_hash(scope: dict, body: bytes) -> str:
        payload = hashlib.sha256()
        payload.update(scope.get("method", "").encode("utf-8"))
        payload.update(scope.get("path", "").encode("utf-8"))
        payload.update(scope.get("query_string", b""))
        payload.update(body)
        return payload.hexdigest()

    @staticmethod
    def _user_identifier(scope: dict) -> str:
        cookie_header = IdempotencyMiddleware._header_value(scope, b"cookie")
        if cookie_header:
            cookies = SimpleCookie()
            cookies.load(cookie_header)
            morsel = cookies.get(settings.access_cookie_name)
            if morsel and morsel.value:
                try:
                    payload = decode_token(morsel.value)
                    user_id = payload.get("sub")
                    token_type = payload.get("type")
                    if user_id and token_type == "access":
                        return str(user_id)
                except Exception:
                    pass

        client = scope.get("client")
        client_ip = client[0] if client and len(client) > 0 else "unknown"
        return f"ip:{client_ip}"

    @staticmethod
    async def _send_json(send, status_code: int, content: dict) -> None:
        body = json.dumps(content).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": status_code,
                "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode("ascii"))],
            }
        )
        await send({"type": "http.response.body", "body": body, "more_body": False})

    @staticmethod
    def _headers_to_jsonable(headers: list[tuple[bytes, bytes]]) -> list[list[str]]:
        return [[name.decode("latin-1"), value.decode("latin-1")] for name, value in headers]

    @staticmethod
    def _jsonable_to_headers(raw_headers: object) -> list[tuple[bytes, bytes]]:
        if isinstance(raw_headers, dict):
            return [
                (str(name).encode("latin-1"), str(value).encode("latin-1"))
                for name, value in raw_headers.items()
            ]
        if isinstance(raw_headers, list):
            parsed: list[tuple[bytes, bytes]] = []
            for item in raw_headers:
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    parsed.append((str(item[0]).encode("latin-1"), str(item[1]).encode("latin-1")))
            return parsed
        return []

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        method = str(scope.get("method", "")).upper()
        if method not in {"POST", "PUT", "PATCH"}:
            await self.app(scope, receive, send)
            return

        idempotency_key = self._header_value(scope, b"idempotency-key")
        if not idempotency_key:
            await self.app(scope, receive, send)
            return

        request_body_chunks: list[bytes] = []
        buffered_followup_messages: list[dict] = []
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                buffered_followup_messages.append(message)
                break
            if message["type"] != "http.request":
                buffered_followup_messages.append(message)
                continue
            request_body_chunks.append(message.get("body", b""))
            if not message.get("more_body", False):
                break
        request_body = b"".join(request_body_chunks)

        request_hash = self._request_hash(scope, request_body)
        user_identifier = self._user_identifier(scope)
        cache_key = f"idempotency:{user_identifier}:{idempotency_key}"

        try:
            cached = await self.redis.get(cache_key)
        except Exception:
            logger.warning(
                "idempotency_redis_read_unavailable_fail_open",
                extra={"path": scope.get("path", ""), "user_identifier": user_identifier},
            )
            if settings.idempotency_fail_closed:
                await self._send_json(
                    send,
                    503,
                    {
                        "detail": "Idempotency service unavailable",
                        "mode": "fail_closed",
                    },
                )
                return
            await self.app(scope, self._build_replay_receive(request_body, receive, buffered_followup_messages), send)
            return

        if cached:
            record = json.loads(cached)
            if record.get("request_hash") != request_hash:
                await self._send_json(send, 409, {"detail": "Idempotency key reuse with different payload"})
                return

            response_body = base64.b64decode(record.get("body_base64", ""))
            response_headers = self._jsonable_to_headers(record.get("headers", []))
            await send(
                {
                    "type": "http.response.start",
                    "status": int(record.get("status_code", 200)),
                    "headers": response_headers,
                }
            )
            await send({"type": "http.response.body", "body": response_body, "more_body": False})
            return

        replay_receive = self._build_replay_receive(request_body, receive, buffered_followup_messages)
        response_start = None
        response_body_chunks: list[bytes] = []

        async def capture_send(message):
            nonlocal response_start
            if message["type"] == "http.response.start":
                response_start = {
                    "status": message.get("status", 200),
                    "headers": list(message.get("headers", [])),
                }
                return
            if message["type"] == "http.response.body":
                response_body_chunks.append(message.get("body", b""))
                return

            if message["type"] == "http.response.debug":
                return

        await self.app(scope, replay_receive, capture_send)

        if response_start is None:
            return

        response_body = b"".join(response_body_chunks)
        record = {
            "request_hash": request_hash,
            "status_code": response_start["status"],
            "headers": self._headers_to_jsonable(response_start["headers"]),
            "body_base64": base64.b64encode(response_body).decode("utf-8"),
        }

        try:
            await self.redis.set(cache_key, json.dumps(record), ex=self.ttl_seconds)
        except Exception:
            logger.warning(
                "idempotency_redis_write_unavailable_fail_open",
                extra={"path": scope.get("path", ""), "user_identifier": user_identifier},
            )
            if settings.idempotency_fail_closed:
                await self._send_json(
                    send,
                    503,
                    {
                        "detail": "Idempotency service unavailable",
                        "mode": "fail_closed",
                    },
                )
                return

        await send(
            {
                "type": "http.response.start",
                "status": int(response_start["status"]),
                "headers": response_start["headers"],
            }
        )
        await send({"type": "http.response.body", "body": response_body, "more_body": False})

    @staticmethod
    def _build_replay_receive(body: bytes, original_receive, prefetched_messages: list[dict]):
        consumed = False

        async def replay_receive():
            nonlocal consumed
            if consumed:
                if prefetched_messages:
                    return prefetched_messages.pop(0)
                return await original_receive()
            consumed = True
            return {"type": "http.request", "body": body, "more_body": False}

        return replay_receive
