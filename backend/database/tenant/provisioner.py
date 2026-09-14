from typing import TYPE_CHECKING

from loguru import logger
from sqlalchemy import text

from backend.core.config import settings
from backend.database.postgres import async_engine
from backend.database.tenant.naming import build_tenant_schema_name

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

__all__ = [
    'check_tenant_schema_exists',
    'create_tenant_schema',
    'drop_tenant_schema',
]


async def create_tenant_schema(tenant_id: str, *, engine: AsyncEngine | None = None) -> str:
    """在 PostgreSQL 中原子创建租户物理 Schema 沙箱.

    Args:
        tenant_id: 租户公开标识 UID。
        engine: 目标数据库引擎，默认使用全局 async_engine。

    Returns:
        str: 实际创建成功的物理 Schema 名称。

    Raises:
        RuntimeError: 单租户模式下调用时抛出。
        ValueError: 租户标识不合法时抛出。
    """
    if not settings.TENANT_ENABLED:
        raise RuntimeError('系统当前运行于单租户模式 (TENANT_ENABLED=False)，不支持开辟独立租户沙箱')

    schema_name = build_tenant_schema_name(tenant_id)
    target_engine = engine or async_engine

    # 使用双引号强约束安全标识符，防范 SQL 注入
    create_sql = text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"')

    async with target_engine.begin() as conn:
        await conn.execute(create_sql)

    logger.info('已成功为租户创建物理 Schema 沙箱: {} (tenant_id={})', schema_name, tenant_id)
    return schema_name


async def check_tenant_schema_exists(tenant_id: str, *, engine: AsyncEngine | None = None) -> bool:
    """检查指定租户的物理 Schema 是否在数据库中真实存在.

    Args:
        tenant_id: 租户公开标识 UID。
        engine: 目标数据库引擎。

    Returns:
        bool: 存在返回 True，不存在返回 False。
    """
    schema_name = build_tenant_schema_name(tenant_id)
    target_engine = engine or async_engine

    query = text('SELECT 1 FROM information_schema.schemata WHERE schema_name = :schema_name')
    async with target_engine.connect() as conn:
        result = await conn.execute(query, {'schema_name': schema_name})
        return result.scalar() is not None


async def drop_tenant_schema(tenant_id: str, *, cascade: bool = False, engine: AsyncEngine | None = None) -> None:
    """安全销毁指定租户的物理 Schema 沙箱 (常用于租户注销或自动化集成测试清理).

    Args:
        tenant_id: 租户公开标识 UID。
        cascade: 是否级联删除 Schema 下的所有表与对象。
        engine: 目标数据库引擎。
    """
    if not settings.TENANT_ENABLED:
        raise RuntimeError('系统当前运行于单租户模式，无法执行租户沙箱销毁操作')

    schema_name = build_tenant_schema_name(tenant_id)
    target_engine = engine or async_engine

    cascade_clause = 'CASCADE' if cascade else 'RESTRICT'
    drop_sql = text(f'DROP SCHEMA IF EXISTS "{schema_name}" {cascade_clause}')

    async with target_engine.begin() as conn:
        await conn.execute(drop_sql)

    logger.warning('已物理销毁租户 Schema 沙箱: {} (cascade={})', schema_name, cascade)
