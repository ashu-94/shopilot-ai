"""Request boundary protections shared by API routes."""

import json

from starlette.responses import JSONResponse

from backend.config import settings


class RequestBoundary:
    def __init__(self, app, max_bytes=65536):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        origin = headers.get(b"origin", b"").decode("latin1")
        cookie_operation = scope["path"].startswith("/api/auth/") and scope["method"] == "POST"
        if cookie_operation and (
            (origin and origin not in settings().cors_origins)
            or (settings().app_env == "production" and b"cookie" in headers and not origin)
        ):
            return await JSONResponse(
                {"error": {"code": "origin_forbidden", "message": "Request origin is not allowed."}},
                status_code=403,
            )(scope, receive, send)
        if scope["method"] in {"POST", "PUT", "PATCH"}:
            body = bytearray()
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                body.extend(message.get("body", b""))
                if len(body) > self.max_bytes:
                    return await JSONResponse(
                        {"error": {"code": "request_too_large", "message": "Request exceeds 64 KiB."}},
                        status_code=413,
                    )(scope, receive, send)
                if not message.get("more_body", False):
                    break
            if body and scope["path"].startswith("/api/"):
                try:
                    json.loads(body)
                except (ValueError, UnicodeDecodeError):
                    return await JSONResponse(
                        {"error": {"code": "invalid_json", "message": "Send a valid JSON request."}},
                        status_code=400,
                    )(scope, receive, send)
            delivered = False

            async def replay():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()

            return await self.app(scope, replay, send)
        return await self.app(scope, receive, send)
