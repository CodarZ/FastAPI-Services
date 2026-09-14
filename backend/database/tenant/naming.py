import re

from backend.core.config import settings

__all__ = [
    'build_tenant_schema_name',
    'extract_tenant_id_from_schema',
    'validate_tenant_id',
]

# 允许的租户业务标识规则: 1~50 位小写字母、数字或下划线 (以字母开头)
_TENANT_ID_REGEX = re.compile(r'^[a-z0-9_]{1,50}$')


def validate_tenant_id(tenant_id: str) -> bool:
    """校验租户标识合法性 (防 SQL 注入与非法字符).

    Args:
        tenant_id: 待校验的租户标识字符串。

    Returns:
        bool: 符合安全命名规则返回 True，否则返回 False。
    """
    if not tenant_id or not isinstance(tenant_id, str):
        return False
    # 转为小写处理
    clean_id = tenant_id.strip().lower()
    return bool(_TENANT_ID_REGEX.fullmatch(clean_id))


def build_tenant_schema_name(tenant_id: str) -> str:
    """安全拼装租户物理 Schema 命名.

    拼接格式为 '{prefix}{tenant_id}' (如 'tenant_org_01')，全小写，总长度不超过 63 字符。

    Args:
        tenant_id: 租户业务标识。

    Returns:
        str: 校验通过的物理 Schema 名称。

    Raises:
        ValueError: 租户标识不合法时抛出。
    """
    if not validate_tenant_id(tenant_id):
        raise ValueError(
            f'非法的租户标识: "{tenant_id}"。租户标识仅支持 1~50 位字母、数字与下划线，禁止包含特殊符号或空格。'
        )
    clean_id = tenant_id.strip().lower()
    schema_name = f'{settings.TENANT_SCHEMA_PREFIX}{clean_id}'

    # PostgreSQL 标识符最长 63 字符
    if len(schema_name) > 63:
        raise ValueError(f'计算生成的租户 Schema 长度 ({len(schema_name)}) 超过 PostgreSQL 上限 (63 字符)')

    return schema_name


def extract_tenant_id_from_schema(schema_name: str) -> str | None:
    """从物理 Schema 名称反解提取租户业务标识.

    若非租户 Schema (如 'public') 或未匹配此前缀，则返回 None。
    """
    if not schema_name or not schema_name.startswith(settings.TENANT_SCHEMA_PREFIX):
        return None
    raw_id = schema_name[len(settings.TENANT_SCHEMA_PREFIX) :]
    return raw_id if validate_tenant_id(raw_id) else None
