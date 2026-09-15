import re
import uuid

from typing import TYPE_CHECKING

from backend.core.config import settings

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = [
    'gen_trace_id',
    'parse_trace_id',
]

# 允许的入站 trace_id 正则白名单
_TRACE_ID_PATTERN = re.compile(r'^[A-Za-z0-9_.\-]{1,64}$')


def gen_trace_id() -> str:
    """生成 Trace ID."""
    return uuid.uuid7().hex


def parse_trace_id(headers: Mapping[str, str]) -> str:
    """从入站请求头安全提取 Trace ID."""
    raw = headers.get(settings.TRACE_ID_HEADER)
    if raw and _TRACE_ID_PATTERN.fullmatch(raw):
        return raw
    return gen_trace_id()
