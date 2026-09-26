from datetime import datetime
from functools import partial

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.enum.custom import StatusType, UserType
from backend.common.model.base import Base
from backend.common.model.mixins import AuditMixin, DateTimeMixin, SoftDeleteMixin
from backend.common.model.types import id_key, json_key, rel_key, uid_key
from backend.utils.uid import gen_uid

__all__ = [
    'SysUser',
    'SysUserPasskey',
    'SysUserSocial',
]


class SysUser(Base, DateTimeMixin, AuditMixin, SoftDeleteMixin):
    """系统用户表."""

    __tablename__ = 'sys_user'
    __table_args__ = (
        Index('uq_sys_user_username_active', 'username', unique=True, postgresql_where=text('deleted_at IS NULL')),
        Index('uq_sys_user_phone_active', 'phone', unique=True, postgresql_where=text('deleted_at IS NULL')),
        Index('uq_sys_user_email_active', 'email', unique=True, postgresql_where=text('deleted_at IS NULL')),
        {'schema': 'tenant', 'comment': '系统用户表'},
    )

    id: Mapped[id_key]
    uid: Mapped[uid_key] = mapped_column(insert_default=partial(gen_uid, 'usr'))

    username: Mapped[str] = mapped_column(String(64), index=True, comment='用户名')
    password: Mapped[str | None] = mapped_column(String(255), comment='密码哈希')

    nickname: Mapped[str] = mapped_column(String(64), comment='用户昵称')
    phone: Mapped[str | None] = mapped_column(String(16), index=True, comment='手机号码')
    email: Mapped[str | None] = mapped_column(String(128), index=True, comment='电子邮箱')
    avatar: Mapped[str | None] = mapped_column(String(255), comment='头像地址')
    dept_id: Mapped[rel_key | None] = mapped_column(comment='部门 ID (逻辑关联)')

    user_type: Mapped[int] = mapped_column(
        SmallInteger,
        default=UserType.MEMBER,
        server_default=text(str(UserType.MEMBER.value)),
        comment='用户身份 (1=超管 2=主管理 3=成员)',
    )
    status: Mapped[int] = mapped_column(
        SmallInteger,
        default=StatusType.ENABLE,
        server_default=text(str(StatusType.ENABLE.value)),
        comment='账号状态 (0=停用 1=正常)',
    )

    token_version: Mapped[int] = mapped_column(Integer, default=1, server_default=text('1'), comment='令牌版本号')
    login_failed_count: Mapped[int] = mapped_column(
        SmallInteger,
        default=0,
        server_default=text('0'),
        comment='连续登录失败次数',
    )
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment='锁定截止时间')
    allowed_ip_range: Mapped[str | None] = mapped_column(String(512), comment='允许登录 IP 范围')

    is_mfa_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text('false'),
        comment='是否启用 MFA',
    )
    mfa_secret: Mapped[str | None] = mapped_column(String(64), comment='MFA 密钥')
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment='最后登录时间')
    last_login_ip: Mapped[str | None] = mapped_column(String(64), comment='最后登录 IP')


class SysUserSocial(Base, DateTimeMixin):
    """用户三方账号绑定表."""

    __tablename__ = 'sys_user_social'
    __table_args__ = (
        UniqueConstraint('source', 'open_id'),
        Index('ix_sys_user_social_user_source', 'user_id', 'source'),
        {'schema': 'tenant', 'comment': '用户三方账号绑定表'},
    )

    id: Mapped[id_key]

    user_id: Mapped[rel_key] = mapped_column(comment='用户 ID (逻辑关联)')
    source: Mapped[str] = mapped_column(String(32), comment='三方渠道标识')

    open_id: Mapped[str] = mapped_column(String(128), comment='平台唯一标识')
    union_id: Mapped[str | None] = mapped_column(String(128), index=True, comment='跨应用统一标识')
    raw_data: Mapped[json_key | None] = mapped_column(comment='三方原始数据')


class SysUserPasskey(Base, DateTimeMixin):
    """用户通行证密钥凭据表."""

    __tablename__ = 'sys_user_passkey'
    __table_args__ = {'schema': 'tenant', 'comment': '用户通行证密钥凭据表'}

    id: Mapped[id_key]

    user_id: Mapped[rel_key] = mapped_column(comment='用户 ID (逻辑关联)')
    credential_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, comment='通行证凭据 ID')
    public_key: Mapped[str] = mapped_column(Text, comment='公钥数据')
    sign_count: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'), comment='签名计数器')
    device_name: Mapped[str] = mapped_column(String(64), comment='设备名称')
    transports: Mapped[str | None] = mapped_column(String(128), comment='传输通道')
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment='最后使用时间')
