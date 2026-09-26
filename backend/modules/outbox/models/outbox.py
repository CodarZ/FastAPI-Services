from datetime import datetime
from functools import partial

from sqlalchemy import DateTime, Index, Integer, SmallInteger, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.enum.custom import OutboxStatusType
from backend.common.model.base import Base
from backend.common.model.mixins import DateTimeMixin
from backend.common.model.types import id_key, json_key, uid_key
from backend.utils.uid import gen_uid

__all__ = ['SysOutbox']


class SysOutbox(Base, DateTimeMixin):
    """本地事务发件箱表."""

    __tablename__ = 'sys_outbox'
    __table_args__ = (
        Index('ix_sys_outbox_status_next_retry', 'status', 'next_retry_at'),
        {'schema': 'tenant', 'comment': '本地事务发件箱表'},
    )

    id: Mapped[id_key]
    uid: Mapped[uid_key] = mapped_column(insert_default=partial(gen_uid, 'obx'))

    event_type: Mapped[str] = mapped_column(String(128), index=True, comment='事件类型')
    payload: Mapped[json_key] = mapped_column(default=dict, server_default=text("'{}'"), comment='事件载荷')
    status: Mapped[int] = mapped_column(
        SmallInteger,
        default=OutboxStatusType.PENDING,
        server_default=text(str(OutboxStatusType.PENDING.value)),
        index=True,
        comment='事件状态 (0=待投递 1=处理中 2=已投递 3=失败)',
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'), comment='重试次数')
    max_retries: Mapped[int] = mapped_column(Integer, default=3, server_default=text('3'), comment='最大重试次数 3 次')
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True, comment='下次重试时间')
    error_message: Mapped[str | None] = mapped_column(Text, comment='错误消息')
