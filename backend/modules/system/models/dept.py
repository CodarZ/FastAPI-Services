from functools import partial

from sqlalchemy import Integer, SmallInteger, String, or_, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.enum.custom import StatusType
from backend.common.model.base import Base
from backend.common.model.mixins import AuditMixin, DateTimeMixin
from backend.common.model.types import id_key, rel_key, uid_key
from backend.utils.uid import gen_uid

__all__ = ['SysDept']


class SysDept(Base, DateTimeMixin, AuditMixin):
    """组织机构部门表."""

    __tablename__ = 'sys_dept'
    __table_args__ = {'schema': 'tenant', 'comment': '组织机构部门表'}

    id: Mapped[id_key]
    uid: Mapped[uid_key] = mapped_column(insert_default=partial(gen_uid, 'dpt'))

    parent_id: Mapped[rel_key | None] = mapped_column(comment='上级部门 ID')
    ancestors: Mapped[str] = mapped_column(
        String(512),
        default='',
        server_default=text("''"),
        comment='祖级列表 (前后逗号定界, 如 ,1,2,)',
    )

    name: Mapped[str] = mapped_column(String(64), comment='部门名称')
    leader: Mapped[str | None] = mapped_column(String(32), comment='负责人')
    phone: Mapped[str | None] = mapped_column(String(16), comment='联系电话')
    email: Mapped[str | None] = mapped_column(String(128), comment='邮箱')

    sort: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'), comment='排序')
    status: Mapped[int] = mapped_column(
        SmallInteger,
        default=StatusType.ENABLE,
        server_default=text(str(StatusType.ENABLE.value)),
        comment='部门状态 (0=停用 1=正常)',
    )
    remark: Mapped[str | None] = mapped_column(String(255), comment='备注')

    @classmethod
    def subtree_condition(cls, dept_id: int):
        """生成查询指定部门及其所有下属子节点的 SQLAlchemy 条件表达式."""
        return or_(cls.id == dept_id, cls.ancestors.like(f'%,{dept_id},%'))

    @classmethod
    def format_ancestors(cls, parent_id: int | None, parent_ancestors: str = '') -> str:
        """生成标准前后带逗号定界的祖级路径串 (如 ',1,2,')."""
        if not parent_id:
            return ''
        clean_anc = parent_ancestors.strip(',')
        return f',{clean_anc},{parent_id},' if clean_anc else f',{parent_id},'
