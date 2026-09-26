from functools import partial
from typing import Any

from sqlalchemy import SmallInteger, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.enum.custom import DataRuleExpressionType, StatusType
from backend.common.model.base import Base
from backend.common.model.mixins import AuditMixin, DateTimeMixin
from backend.common.model.types import id_key, uid_key
from backend.utils.uid import gen_uid

__all__ = ['SysDataRule']


class SysDataRule(Base, DateTimeMixin, AuditMixin):
    """数据权限规则表."""

    __tablename__ = 'sys_data_rule'
    __table_args__ = {'schema': 'tenant', 'comment': '数据权限规则表'}

    id: Mapped[id_key]
    uid: Mapped[uid_key] = mapped_column(insert_default=partial(gen_uid, 'rul'))

    name: Mapped[str] = mapped_column(String(64), comment='规则名称')
    model_name: Mapped[str] = mapped_column(String(64), index=True, comment='目标模型')
    field_name: Mapped[str] = mapped_column(String(64), comment='过滤字段')
    expression: Mapped[str] = mapped_column(
        String(16),
        default=DataRuleExpressionType.EQ,
        server_default=text("'eq'"),
        comment='运算符 (eq/ne/gt/gte/lt/lte/like/in/not_in/is_null)',
    )
    rule_value: Mapped[str] = mapped_column(Text, comment='规则值')

    status: Mapped[int] = mapped_column(
        SmallInteger,
        default=StatusType.ENABLE,
        server_default=text(str(StatusType.ENABLE.value)),
        comment='状态 (0=停用 1=正常)',
    )
    remark: Mapped[str | None] = mapped_column(String(255), comment='备注')

    @classmethod
    def coerce_value(cls, column: Any, raw_val: str) -> Any:
        """利用 SQLAlchemy 将文本值转换为列的原生 Python 标量类型."""
        py_type = getattr(column.type, 'python_type', str)
        if py_type is bool:
            return raw_val.strip().lower() in ('true', 't', '1', 'yes', 'y', 'on')
        if issubclass(py_type, int):
            return int(raw_val.strip())
        if issubclass(py_type, float):
            return float(raw_val.strip())
        return str(raw_val)

    @classmethod
    def build_expression(cls, column: Any, op: str, raw_val: str) -> Any:
        """基于纯原生 SQLAlchemy AST 构建参数化二元比较表达式."""
        if op == DataRuleExpressionType.IS_NULL:
            return column.is_(None)
        if op == DataRuleExpressionType.IS_NOT_NULL:
            return column.is_not(None)

        if op in (DataRuleExpressionType.IN, DataRuleExpressionType.NOT_IN):
            # 将逗号分隔字符串逐项转换为目标标量类型
            items = [cls.coerce_value(column, x) for x in raw_val.split(',') if x.strip()]
            return column.in_(items) if op == DataRuleExpressionType.IN else column.not_in(items)

        # 单值转换
        val = cls.coerce_value(column, raw_val)
        if op == DataRuleExpressionType.EQ:
            return column == val
        if op == DataRuleExpressionType.NE:
            return column != val
        if op == DataRuleExpressionType.GT:
            return column > val
        if op == DataRuleExpressionType.GTE:
            return column >= val
        if op == DataRuleExpressionType.LT:
            return column < val
        if op == DataRuleExpressionType.LTE:
            return column <= val
        if op == DataRuleExpressionType.LIKE:
            return column.like(str(val))
        return column == val
