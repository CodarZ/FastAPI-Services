from functools import partial

from sqlalchemy import Boolean, Integer, SmallInteger, String, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.enum.custom import MenuType, StatusType
from backend.common.model.base import Base
from backend.common.model.mixins import AuditMixin, DateTimeMixin
from backend.common.model.types import id_key, rel_key, uid_key
from backend.utils.uid import gen_uid

__all__ = ['SysMenu']


class SysMenu(Base, DateTimeMixin, AuditMixin):
    """系统菜单权限表."""

    __tablename__ = 'sys_menu'
    __table_args__ = {'schema': 'tenant', 'comment': '系统菜单权限表'}

    id: Mapped[id_key]
    uid: Mapped[uid_key] = mapped_column(insert_default=partial(gen_uid, 'mnu'))

    parent_id: Mapped[rel_key | None] = mapped_column(comment='上级菜单 ID')
    name: Mapped[str] = mapped_column(String(64), comment='菜单名称')
    menu_type: Mapped[int] = mapped_column(
        SmallInteger,
        default=MenuType.MENU,
        server_default=text(str(MenuType.MENU.value)),
        comment='菜单类型 (0=目录 1=菜单 2=按钮 3=内嵌 4=外链)',
    )
    path: Mapped[str | None] = mapped_column(String(255), comment='路由地址')
    component: Mapped[str | None] = mapped_column(String(255), comment='组件路径')
    perms: Mapped[str | None] = mapped_column(String(128), index=True, comment='权限标识')
    icon: Mapped[str | None] = mapped_column(String(128), comment='图标')

    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text('true'), comment='是否显示')
    is_cache: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text('false'), comment='是否缓存')

    sort: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'), comment='显示排序')
    status: Mapped[int] = mapped_column(
        SmallInteger,
        default=StatusType.ENABLE,
        server_default=text(str(StatusType.ENABLE.value)),
        comment='菜单状态 (0=停用 1=正常)',
    )
    remark: Mapped[str | None] = mapped_column(String(255), comment='备注')
