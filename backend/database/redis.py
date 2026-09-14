from loguru import logger
from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import RedisError

from backend.core.config import settings

__all__ = [
    'check_redis_health',
    'close_redis_pool',
    'create_redis_client',
    'create_redis_pool',
    'init_redis_pool',
    'redis_client',
    'redis_pool',
]


def create_redis_pool(
    url: str | None = None,
    *,
    max_connections: int | None = None,
    timeout: int | None = None,
) -> ConnectionPool:
    """创建异步 Redis 连接池实例."""
    redis_url = url or settings.REDIS_URL
    max_conn = max_connections if max_connections is not None else settings.REDIS_MAX_CONNECTIONS
    socket_timeout = timeout if timeout is not None else settings.REDIS_TIMEOUT

    return ConnectionPool.from_url(
        redis_url,
        max_connections=max_conn,
        socket_timeout=socket_timeout,
        socket_connect_timeout=socket_timeout,
        decode_responses=True,
    )


def create_redis_client(pool: ConnectionPool | None = None) -> Redis:
    """创建与指定连接池绑定的异步 Redis 客户端."""
    return Redis(connection_pool=pool or redis_pool)


# 全局连接池与客户端单例
redis_pool: ConnectionPool = create_redis_pool()
redis_client: Redis = create_redis_client(redis_pool)


def init_redis_pool(url: str | None = None, **kwargs: object) -> None:
    """重新初始化全局 Redis 连接池与客户端单例."""
    global redis_client, redis_pool
    redis_pool = create_redis_pool(url=url, **kwargs)
    redis_client = create_redis_client(redis_pool)
    logger.info('全局 Redis 连接池已成功初始化')


async def close_redis_pool(client: Redis | None = None) -> None:
    """平滑关闭 Redis 客户端并释放连接池连接."""
    target_client = client or redis_client
    await target_client.close()
    if target_client.connection_pool is not None:
        await target_client.connection_pool.disconnect()
    logger.info('Redis 连接池已安全释放')


async def check_redis_health(client: Redis | None = None) -> bool:
    """Redis 健康检查."""
    target_client = client or redis_client
    try:
        pong = await target_client.ping()
    except (RedisError, OSError) as exc:
        logger.warning('Redis 健康探活失败: {}', exc)
        return False
    else:
        return bool(pong)
