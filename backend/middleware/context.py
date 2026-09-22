from typing import TYPE_CHECKING

from starlette.datastructures import Headers, MutableHeaders

from backend.common.model.dataclasses import ClientContext
from backend.common.request.context import bind_context
from backend.common.request.parse import lookup_ip_region, parse_client_ip
from backend.common.request.trace_id import parse_trace_id
from backend.core.config import settings

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send

__all__ = ['ContextMiddleware']


class ContextMiddleware:
    """全链路请求上下文绑定中间件."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] not in ('http', 'websocket'):
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        trace_id = parse_trace_id(headers)

        # 将 TraceID 写入 ASGI scope，供外层异常处理器读取
        scope.setdefault('state', {})['trace_id'] = trace_id

        # 传入已解析的 headers 实例
        client_ip = parse_client_ip(scope, headers=headers)
        raw_ua = headers.get('user-agent')
        region = lookup_ip_region(client_ip) if settings.IP2REGION_ENABLED else None
        client = ClientContext(ip=client_ip, user_agent=raw_ua, ip_region=region)

        async def send_with_trace(message: Message) -> None:
            if message['type'] == 'http.response.start':
                mutable_headers = MutableHeaders(scope=message)
                # 杜绝下游多次拦截出现重复的 TraceID 头部
                mutable_headers[settings.TRACE_ID_HEADER] = trace_id
            await send(message)

        target_send = send_with_trace if scope['type'] == 'http' else send

        async with bind_context(trace_id=trace_id, client=client):
            await self.app(scope, receive, target_send)
