from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.request import ctx
from backend.core.config import settings
from backend.database.postgres import async_engine, async_session_factory
from backend.database.tenant.naming import build_tenant_schema_name

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

__all__ = [
    'get_public_db',
    'get_tenant_db',
    'get_tenant_db_by_id',
    'resolve_tenant_schema',
]


def resolve_tenant_schema(tenant_id: str | None = None) -> str:
    """获取 Schema 名称.

    若全局未启用多租户 (TENANT_ENABLED=False)，无论是否传入 tenant_id 均统一平滑回退至公共 Schema；
    若启用多租户，则必须提供有效 tenant_id，并通过 build_tenant_schema_name 执行严格防注入校验。

    Args:
        tenant_id: 租户公开标识 UID。

    Returns:
        str: 目标物理 Schema 名称 (如 'public' 或 'tenant_xxx')。

    Raises:
        RuntimeError: 启用多租户但缺少有效 tenant_id 时抛出。
        ValueError: 租户标识不符合安全规范时抛出。
    """
    if not settings.TENANT_ENABLED:
        return settings.TENANT_DEFAULT_SCHEMA

    target_id = tenant_id or ctx.tenant_id
    if not target_id:
        raise RuntimeError('多租户模式已启用，但请求上下文中未检测到有效租户标识')

    # 调用专用命名模块执行正则防注入与长度约束
    return build_tenant_schema_name(target_id)


async def get_public_db() -> AsyncGenerator[AsyncSession]:
    """FastAPI 依赖注入器: 获取公共/平台级数据库会话."""
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_tenant_db() -> AsyncGenerator[AsyncSession]:
    """FastAPI 依赖注入器: 隐式从当前请求上下文获取租户专属数据库会话.

    单租户模式下自动透明降级回退至 public。
    """
    schema_name = resolve_tenant_schema()
    tenant_engine = async_engine.execution_options(
        schema_translate_map={'tenant': schema_name},
    )
    session = AsyncSession(
        bind=tenant_engine,
        autoflush=False,
        expire_on_commit=False,
    )
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


@asynccontextmanager
async def get_tenant_db_by_id(tenant_id: str) -> AsyncGenerator[AsyncSession]:
    """异步上下文管理器: 显式根据指定租户 ID 获取该租户的数据库会话.

    专供平台超级管理员代客操作、异步 Worker 任务调度或离线自动化测试使用。

    Args:
        tenant_id: 租户公开标识 UID。

    Yields:
        AsyncSession: 绑定目标租户 Schema 翻译的异步会话。
    """
    schema_name = resolve_tenant_schema(tenant_id)
    tenant_engine = async_engine.execution_options(
        schema_translate_map={'tenant': schema_name},
    )
    session = AsyncSession(
        bind=tenant_engine,
        autoflush=False,
        expire_on_commit=False,
    )
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
