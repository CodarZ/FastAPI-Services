from typing import Annotated, Any

from sqlalchemy import BigInteger, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column

from backend.utils.uid import gen_uid

__all__ = [
    'id_key',
    'json_key',
    'rel_key',
    'uid_key',
]

# 内部物理主键 ID (不对外暴露)
id_key = Annotated[
    int,
    mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        sort_order=-100,
        comment='物理自增主键',
    ),
]

# 对外公开业务短 UID
uid_key = Annotated[
    str,
    mapped_column(
        String(32),
        unique=True,
        sort_order=-99,
        default=gen_uid,
        comment='业务全局唯一短 UID',
    ),
]

# 逻辑关联外键列
rel_key = Annotated[int, mapped_column(BigInteger, index=True)]

# JSONB 结构化载荷
json_key = Annotated[dict[str, Any], mapped_column(JSONB)]
