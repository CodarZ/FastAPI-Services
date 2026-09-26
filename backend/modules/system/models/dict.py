from sqlalchemy import Boolean, Integer, SmallInteger, String, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.enum.custom import StatusType
from backend.common.model.base import Base
from backend.common.model.mixins import AuditMixin, DateTimeMixin
from backend.common.model.types import id_key, uid_key

__all__ = [
    'SysDictData',
    'SysDictType',
]


class SysDictType(Base, DateTimeMixin, AuditMixin):
    """数据字典类型表."""

    __tablename__ = 'sys_dict_type'
    __table_args__ = {'schema': 'tenant', 'comment': '数据字典类型表'}

    id: Mapped[id_key]
    uid: Mapped[uid_key]

    dict_name: Mapped[str] = mapped_column(String(64), comment='字典名称')
    dict_type: Mapped[str] = mapped_column(String(64), unique=True, index=True, comment='字典类型')

    status: Mapped[int] = mapped_column(
        SmallInteger,
        default=StatusType.ENABLE,
        server_default=text(str(StatusType.ENABLE.value)),
        comment='状态 (0=停用 1=正常)',
    )
    remark: Mapped[str | None] = mapped_column(String(255), comment='备注')


class SysDictData(Base, DateTimeMixin, AuditMixin):
    """数据字典数据项表."""

    __tablename__ = 'sys_dict_data'
    __table_args__ = {'schema': 'tenant', 'comment': '数据字典数据项表'}

    id: Mapped[id_key]
    uid: Mapped[uid_key]

    dict_type: Mapped[str] = mapped_column(String(64), index=True, comment='字典类型')
    dict_label: Mapped[str] = mapped_column(String(64), comment='字典标签')
    dict_value: Mapped[str] = mapped_column(String(64), comment='字典键值')

    tag_type: Mapped[str | None] = mapped_column(String(64), comment='组件库预设类型 (如 info/warning/danger)')
    css_class: Mapped[str | None] = mapped_column(String(64), comment='自定义 CSS 类名')
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text('false'), comment='是否默认')

    sort: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'), comment='排序')
    status: Mapped[int] = mapped_column(
        SmallInteger,
        default=StatusType.ENABLE,
        server_default=text(str(StatusType.ENABLE.value)),
        comment='状态 (0=停用 1=正常)',
    )
    remark: Mapped[str | None] = mapped_column(String(255), comment='备注')
