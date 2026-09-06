from enum import IntEnum as SourceIntEnum, StrEnum as SourceStrEnum
from typing import Any

__all__ = [
    'IntEnum',
    'StrEnum',
]


class _EnumBase:
    """枚举混入基类."""

    @classmethod
    def get_values(cls) -> list[Any]:
        """获取所有枚举成员的值列表."""
        return [item.value for item in cls]

    @classmethod
    def get_names(cls) -> list[str]:
        """获取所有枚举成员的名称列表."""
        return [item.name for item in cls]

    @classmethod
    def get_dict(cls) -> dict[str, Any]:
        """获取 {name: value} 形式的字典映射."""
        return {item.name: item.value for item in cls}

    @classmethod
    def has_name(cls, name: str) -> bool:
        """判断是否存在指定成员名称."""
        return name in cls.__members__

    @classmethod
    def has_value(cls, value: Any) -> bool:
        """判断是否存在指定值."""
        return value in cls.get_values()


class IntEnum(_EnumBase, SourceIntEnum):
    """整型业务枚举基类."""


class StrEnum(_EnumBase, SourceStrEnum):
    """字符串业务枚举基类."""
