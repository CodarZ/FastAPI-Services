from datetime import UTC, datetime

from sqlalchemy import BigInteger, Boolean, DateTime, func, text
from sqlalchemy.orm import Mapped, mapped_column

__all__ = [
    'AuditMixin',
    'DateTimeMixin',
    'SoftDeleteMixin',
]


class DateTimeMixin:
    """时间戳审计 Mixin (UTC 时区感知)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        sort_order=90,
        comment='创建时间',
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        sort_order=91,
        comment='更新时间',
    )


class AuditMixin:
    """操作人审计 Mixin (逻辑关联)."""

    created_by: Mapped[int | None] = mapped_column(
        BigInteger,
        default=None,
        sort_order=92,
        comment='创建人 ID',
    )
    updated_by: Mapped[int | None] = mapped_column(
        BigInteger,
        default=None,
        sort_order=93,
        comment='最后修改人 ID',
    )


class SoftDeleteMixin:
    """软删除审计 Mixin."""

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text('false'),
        index=True,
        sort_order=94,
        comment='是否软删除',
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        sort_order=95,
        comment='软删除时间',
    )
    deleted_by: Mapped[int | None] = mapped_column(
        BigInteger,
        default=None,
        sort_order=96,
        comment='执行删除人 ID',
    )
