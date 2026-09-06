from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic.alias_generators import to_snake
from sqlalchemy import MetaData, inspect
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, declared_attr

__all__ = [
    'POSTGRES_NAMING_CONVENTION',
    'Base',
]

# PostgreSQL 约束标准命名规则
POSTGRES_NAMING_CONVENTION: dict[str, str] = {
    'ix': 'ix_%(table_name)s_%(column_0_N_name)s',
    'uq': 'uq_%(table_name)s_%(column_0_N_name)s',
    'ck': 'ck_%(table_name)s_%(constraint_name)s',
    'fk': 'fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s',
    'pk': 'pk_%(table_name)s',
}


class Base(AsyncAttrs, DeclarativeBase):
    """全局统一 ORM 声明式基类."""

    metadata = MetaData(naming_convention=POSTGRES_NAMING_CONVENTION)

    @declared_attr.directive
    @classmethod
    def __tablename__(cls) -> str:
        """转为 snake_case 表名."""
        return to_snake(cls.__name__)

    def __repr__(self) -> str:
        """调试输出，展示业务 uid 或 id，避免触发隐式加载."""
        identity = getattr(self, 'uid', None) or getattr(self, 'id', None)
        return f'<{self.__class__.__name__} {identity}>' if identity else f'<{self.__class__.__name__}>'

    def to_dict(
        self,
        exclude: set[str] | None = None,
        include: set[str] | None = None,
    ) -> dict[str, Any]:
        """将当前 ORM 实例转换为可序列化的标准字典.

        Args:
            exclude: 排除的字段名集合。
            include: 包含的字段名集合。

        Returns:
            序列化后的字典映射。
        """
        exclude_set = exclude or set()

        # 获取 SQLAlchemy 实例状态，用于安全检测属性加载情况
        state = inspect(self)
        # 未加载字段集合
        unloaded = state.unloaded if state is not None else set()
        # 已过期字段集合
        expired = state.expired_attributes if state is not None else set()

        result: dict[str, Any] = {}
        # 仅遍历物理映射列，避免遍历 relationship 引发额外查询
        for column in self.__table__.columns:
            col_name = column.name

            # 白名单与黑名单过滤
            if include is not None and col_name not in include:
                continue
            if col_name in exclude_set:
                continue

            # 跳过未加载或已过期属性
            if col_name in unloaded or col_name in expired:
                continue

            val = getattr(self, col_name, None)

            # 类型序列化转换
            if isinstance(val, (datetime, date, time)):
                result[col_name] = val.isoformat()  # 标准 ISO 8601 字符串
            elif isinstance(val, Enum):
                result[col_name] = val.value
            elif isinstance(val, (UUID, Decimal)):
                result[col_name] = str(val)
            else:
                result[col_name] = val

        return result
