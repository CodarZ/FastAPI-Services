from datetime import datetime
from functools import partial

from sqlalchemy import DateTime, Integer, SmallInteger, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.enum.custom import TenantStatusType
from backend.common.model.base import Base
from backend.common.model.mixins import AuditMixin, DateTimeMixin
from backend.common.model.types import id_key, uid_key
from backend.utils.uid import gen_uid

__all__ = ['SysTenant']


class SysTenant(Base, DateTimeMixin, AuditMixin):
    """平台租户表 (运行于公共控制平面 public Schema)."""

    __tablename__ = 'sys_tenant'
    __table_args__ = {'comment': '平台租户表'}

    id: Mapped[id_key]
    uid: Mapped[uid_key] = mapped_column(insert_default=partial(gen_uid, 'tnt'))

    name: Mapped[str] = mapped_column(String(64), comment='租户名称')
    schema_name: Mapped[str] = mapped_column(String(64), unique=True, index=True, comment='隔离 Schema 名称')

    quota_users: Mapped[int] = mapped_column(Integer, default=20, server_default=text('20'), comment='用户配额上限')
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment='租期截止时间')
    notice_webhook: Mapped[str | None] = mapped_column(String(512), comment='通知 Webhook 地址')
    contact_name: Mapped[str | None] = mapped_column(String(32), comment='联系人姓名')
    contact_phone: Mapped[str | None] = mapped_column(String(16), comment='联系人手机号')
    contact_email: Mapped[str | None] = mapped_column(String(128), comment='联系人邮箱')
    ip_whitelist: Mapped[str | None] = mapped_column(Text, comment='IP 白名单')

    status: Mapped[int] = mapped_column(
        SmallInteger,
        default=TenantStatusType.NORMAL,
        server_default=text(str(TenantStatusType.NORMAL.value)),
        comment='租户状态 (0=待初始化 1=正常 2=冻结 3=到期)',
    )
    remark: Mapped[str | None] = mapped_column(String(255), comment='备注')
