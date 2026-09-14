from loguru import logger
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.core.config import settings

__all__ = [
    'async_engine',
    'async_session_factory',
    'check_db_health',
    'close_db_engine',
    'create_database_engine',
    'create_session_factory',
    'init_db_engine',
]


def create_database_engine(
    url: str | None = None,
    *,
    echo: bool | None = None,
    echo_pool: bool | None = None,
) -> AsyncEngine:
    """创建异步 PostgreSQL 数据库引擎实例."""
    db_url = url or settings.DATABASE_URL
    return create_async_engine(
        db_url,
        echo=echo if echo is not None else settings.DATABASE_ECHO,
        echo_pool=echo_pool if echo_pool is not None else settings.DATABASE_ECHO_POOL,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_timeout=settings.DATABASE_POOL_TIMEOUT,
        pool_recycle=settings.DATABASE_POOL_RECYCLE,
        pool_pre_ping=settings.DATABASE_POOL_PRE_PING,
        pool_use_lifo=settings.DATABASE_POOL_USE_LIFO,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """创建异步会话工厂."""
    return async_sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )


# 全局单例引擎与会话工厂
async_engine: AsyncEngine = create_database_engine()
async_session_factory: async_sessionmaker[AsyncSession] = create_session_factory(async_engine)


def init_db_engine(url: str | None = None, **kwargs: object) -> None:
    """重新初始化引擎与会话工厂 (常用于测试)."""
    global async_engine, async_session_factory
    async_engine = create_database_engine(url=url, **kwargs)
    async_session_factory = create_session_factory(async_engine)
    logger.info('全局数据库引擎已成功初始化: {}', async_engine.url.render_as_string(hide_password=True))


async def close_db_engine(engine: AsyncEngine | None = None) -> None:
    """关闭数据库引擎并释放所有底层连接."""
    target_engine = engine or async_engine
    await target_engine.dispose()
    logger.info('数据库连接池已安全释放')


async def check_db_health(engine: AsyncEngine | None = None) -> bool:
    """PostgreSQL 健康检查."""
    target_engine = engine or async_engine
    try:
        async with target_engine.connect() as conn:
            await conn.execute(text('SELECT 1'))
    except (SQLAlchemyError, OSError) as exc:
        logger.warning('数据库健康探活失败: {}', exc)
        return False
    else:
        return True
