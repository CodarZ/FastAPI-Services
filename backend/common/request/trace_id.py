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
_OTEL_TRACE_ID_REGEX = re.compile(r'^[0-9a-fA-F]{32}$')
_INVALID_ZERO_TRACE_ID = '0' * 32


def gen_trace_id() -> str:
    """生成 Trace ID."""
    return uuid.uuid7().hex


def parse_trace_id(headers: Mapping[str, str]) -> str:
    """从入站请求头安全提取 Trace ID."""
    raw = headers.get(settings.TRACE_ID_HEADER)
    if raw:
        clean_raw = raw.strip()
        if _OTEL_TRACE_ID_REGEX.fullmatch(clean_raw) and clean_raw != _INVALID_ZERO_TRACE_ID:
            return clean_raw.lower()
    return gen_trace_id()
