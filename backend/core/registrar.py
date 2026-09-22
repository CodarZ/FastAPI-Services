from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from backend.common.exception.handler import register_exception_handlers
from backend.common.log import close_logging, log, setup_logging
from backend.core.config import settings
from backend.database.postgres import close_db_engine
from backend.database.redis import close_redis_pool
from backend.middleware.context import ContextMiddleware

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

__all__ = [
    'register_app',
    'register_lifespan',
    'register_middleware',
]


@asynccontextmanager
async def register_lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """全局生命周期管理器."""
    setup_logging()
    log.success('系统服务正在启动，当前运行环境: {}', settings.ENVIRONMENT)

    try:
        yield
    finally:
        # 关闭阶段逆序释放，各资源隔离容错
        log.warning('系统服务正在关闭，开始释放底层物理资源...')
        for teardown, name in (
            (close_db_engine, 'PostgreSQL 数据库连接池'),
            (close_redis_pool, 'Redis 连接池'),
            (close_logging, '日志队列与句柄'),
        ):
            try:
                await teardown()
            except Exception:
                log.exception('释放 {} 时发生异常', name)


def register_middleware(app: FastAPI) -> None:
    """注册全局中间件."""
    # 挂载请求上下文绑定中间件
    app.add_middleware(ContextMiddleware)

    # 挂载跨域 CORS 中间件
    if settings.MIDDLEWARE_CORS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ALLOWED_ORIGINS,
            allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
            allow_methods=settings.CORS_ALLOW_METHODS,
            allow_headers=settings.CORS_ALLOW_HEADERS,
            expose_headers=settings.CORS_EXPOSE_HEADERS,
        )


def register_app(app: FastAPI | None = None) -> FastAPI:
    """初始化 FastAPI 应用实例."""
    if app is None:
        app = FastAPI(
            title=settings.FASTAPI_TITLE,
            version=settings.FASTAPI_VERSION,
            description=settings.FASTAPI_DESCRIPTION,
            docs_url=settings.FASTAPI_DOCS_URL,
            redoc_url=settings.FASTAPI_REDOC_URL,
            openapi_url=settings.FASTAPI_OPENAPI_URL,
            swagger_ui_parameters=settings.FASTAPI_SWAGGER_UI_PARAMETERS,
            lifespan=register_lifespan,
        )

    # 注册中间件
    register_middleware(app)

    # 注册全局异常拦截器
    register_exception_handlers(app)

    return app
