import ipaddress
import threading

from functools import lru_cache
from typing import TYPE_CHECKING

import ip2region.searcher as xdb
import ip2region.util as xdb_util

from starlette.datastructures import Headers
from user_agents import parse as _parse_ua

from backend.common.log import log
from backend.common.model.dataclasses import UserAgentInfo
from backend.core.config import settings
from backend.core.path import IP2REGION_XDB_V4_PATH, IP2REGION_XDB_V6_PATH

if TYPE_CHECKING:
    from starlette.types import Scope

__all__ = [
    'lookup_ip_region',
    'parse_client_ip',
    'parse_user_agent',
]

# 无法确定客户端地址
_UNKNOWN_IP: str = '0.0.0.0'  # nosec B104


def _valid_ip(candidate: str) -> str | None:
    """校验并规范化 IP 字符串，非法返回 None."""
    try:
        address = ipaddress.ip_address(candidate.strip())
    except ValueError, AttributeError:
        return None
    return str(address)


def parse_client_ip(scope: Scope) -> str:
    """提取客户端真实 IP.

    提取顺序:
    1. settings.CLIENT_IP_HEADERS 指定的候选请求头 (逗号分割取最左段，仅当配置非空时读取)；
    2. ASGI scope['client'][0] (由 uvicorn 受信代理机制校验写入)；
    3. '0.0.0.0' 兜底。
    """
    if settings.CLIENT_IP_HEADERS:
        headers = Headers(scope=scope)
        for name in settings.CLIENT_IP_HEADERS:
            raw = headers.get(name)
            if not raw:
                continue
            # 取最左侧首段并校验合法性
            ip = _valid_ip(raw.split(',', 1)[0])
            if ip:
                return ip

    client = scope.get('client')
    if client:
        ip = _valid_ip(client[0])
        if ip:
            return ip

    return _UNKNOWN_IP


@lru_cache(maxsize=2048)
def _cached_parse_user_agent(raw: str) -> UserAgentInfo:
    """带 LRU 缓存的 User-Agent 结构化解析核心."""
    ua = _parse_ua(raw)
    return UserAgentInfo(
        raw=raw,
        browser=ua.browser.family if ua.browser.family != 'Other' else None,
        os=ua.os.family if ua.os.family != 'Other' else None,
        device=ua.device.family if ua.device.family != 'Other' else None,
        is_mobile=ua.is_mobile,
        is_tablet=ua.is_tablet,
        is_pc=ua.is_pc,
        is_bot=ua.is_bot,
    )


def parse_user_agent(user_agent: str | None) -> UserAgentInfo:
    """结构化解析 User-Agent."""
    if not user_agent or not user_agent.strip():
        return UserAgentInfo()

    clean_ua = user_agent.strip()
    # 超过 512 字符截断，杜绝恶意 ReDoS 攻击
    if len(clean_ua) > 512:
        clean_ua = clean_ua[:512]

    return _cached_parse_user_agent(clean_ua)


# 进程级 xdb Searcher 内存单例 (按 IP 版本 4 / 6 缓存)
_searchers: dict[int, xdb.Searcher | None] = {}
_searchers_lock = threading.Lock()


def _load_searcher(version: int) -> xdb.Searcher | None:
    """将 xdb 文件一次性读入内存 Buffer，创建无锁并发安全的纯内存检索器."""
    if version == 4:
        path, xdb_version = IP2REGION_XDB_V4_PATH, xdb_util.IPv4
    else:
        path, xdb_version = IP2REGION_XDB_V6_PATH, xdb_util.IPv6

    if not path.is_file():
        log.debug('ip2region xdb 文件不存在，IPv{} 属地解析不可用: {}', version, path)
        return None

    try:
        content = xdb_util.load_content_from_file(str(path))
        return xdb.new_with_buffer(xdb_version, content)
    except Exception:
        log.exception('ip2region xdb 内存加载失败，IPv{} 属地解析不可用: {}', version, path)
        return None


def _get_searcher(version: int) -> xdb.Searcher | None:
    """加锁单例获取 Searcher 实例."""
    if version not in _searchers:
        with _searchers_lock:
            if version not in _searchers:
                _searchers[version] = _load_searcher(version)
    return _searchers[version]


def lookup_ip_region(ip: str) -> str | None:
    """离线高速查询 IP 物理属地."""
    if not settings.IP2REGION_ENABLED or not ip:
        return None

    try:
        addr = ipaddress.ip_address(ip.strip())
    except ValueError, AttributeError:
        return None

    # 内网私有地址与回环地址短路
    if addr.is_private or addr.is_loopback or addr.is_unspecified:
        return '内网IP'

    searcher = _get_searcher(addr.version)
    if searcher is None:
        return None

    try:
        region = searcher.search(str(addr))
    except Exception:
        log.exception('ip2region 查询执行异常: {}', ip)
        return None
    else:
        return region or None
