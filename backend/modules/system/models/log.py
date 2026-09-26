from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, SmallInteger, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.enum.custom import LogStatusType, OperBusinessType
from backend.common.model.base import Base
from backend.common.model.types import id_key, json_key, rel_key

__all__ = [
    'SysLoginLog',
    'SysOperLog',
]


class SysOperLog(Base):
    """操作审计日志表."""

    __tablename__ = 'sys_oper_log'
    __table_args__ = {'schema': 'tenant', 'comment': '操作审计日志表'}

    id: Mapped[id_key]

    trace_id: Mapped[str] = mapped_column(String(64), index=True, comment='Trace ID')
    user_id: Mapped[rel_key | None] = mapped_column(comment='用户 ID')
    username: Mapped[str | None] = mapped_column(String(64), comment='用户名')
    title: Mapped[str] = mapped_column(String(64), comment='模块标题')
    business_type: Mapped[int] = mapped_column(
        SmallInteger,
        default=OperBusinessType.OTHER,
        server_default=text(str(OperBusinessType.OTHER.value)),
        comment='业务类型 (0=其它 1=新增 2=修改 3=删除 4=查看 5=导出 6=导入 7=授权 8=强退)',
    )
    method: Mapped[str | None] = mapped_column(String(128), comment='调用方法')
    request_method: Mapped[str | None] = mapped_column(String(16), comment='请求方式')
    request_url: Mapped[str | None] = mapped_column(String(255), comment='请求 URL')
    oper_ip: Mapped[str | None] = mapped_column(String(64), comment='操作 IP')
    oper_location: Mapped[str | None] = mapped_column(String(128), comment='操作属地')
    request_param: Mapped[json_key | None] = mapped_column(comment='请求参数')
    status: Mapped[int] = mapped_column(
        SmallInteger,
        default=LogStatusType.SUCCESS,
        server_default=text(str(LogStatusType.SUCCESS.value)),
        comment='操作状态 (0=失败 1=成功)',
    )
    error_msg: Mapped[str | None] = mapped_column(Text, comment='错误消息')
    cost_time: Mapped[int] = mapped_column(BigInteger, default=0, server_default=text('0'), comment='耗时 (毫秒)')
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        sort_order=90,
        comment='操作时间',
    )


class SysLoginLog(Base):
    """登录审计日志表."""

    __tablename__ = 'sys_login_log'
    __table_args__ = {'schema': 'tenant', 'comment': '登录审计日志表'}

    id: Mapped[id_key]

    username: Mapped[str] = mapped_column(String(64), index=True, comment='用户名')
    login_ip: Mapped[str] = mapped_column(String(64), comment='登录 IP')
    login_location: Mapped[str | None] = mapped_column(String(128), comment='登录属地')
    browser: Mapped[str | None] = mapped_column(String(64), comment='浏览器')
    os: Mapped[str | None] = mapped_column(String(64), comment='操作系统')
    status: Mapped[int] = mapped_column(
        SmallInteger,
        default=LogStatusType.SUCCESS,
        server_default=text(str(LogStatusType.SUCCESS.value)),
        comment='登录状态 (0=失败 1=成功)',
    )
    message: Mapped[str | None] = mapped_column(String(255), comment='提示消息')
    login_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        sort_order=90,
        comment='登录时间',
    )
