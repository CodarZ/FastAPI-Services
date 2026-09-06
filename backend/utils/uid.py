import secrets

from datetime import UTC, datetime

__all__ = [
    'gen_uid',
]

# Base62 字符表
_BASE62_ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
_BASE62_LEN = len(_BASE62_ALPHABET)


def _encode_base62(num: int, min_length: int = 8) -> str:
    """将非负整数转换为 Base62 编码字符串，不足 min_length 高位补 0."""
    if num < 0:
        raise ValueError('num 必须为非负整数')
    if num == 0:
        return _BASE62_ALPHABET[0] * min_length

    digits = []
    while num > 0:
        num, rem = divmod(num, _BASE62_LEN)
        digits.append(_BASE62_ALPHABET[rem])

    # 反转顺序，得到正确的 Base62 编码
    encoded = ''.join(reversed(digits))

    # 高位补 0 达到长度要求
    if len(encoded) < min_length:
        encoded = encoded.rjust(min_length, _BASE62_ALPHABET[0])
    return encoded


def gen_uid(prefix: str = '') -> str:
    """生成业务短 UID.

    格式：{prefix}_{time8}{rand6} 或 {time8}{rand6}
    - time8: 基于当前 UTC 毫秒时间戳的 Base62 编码
    - rand6: 6 位随机 Base62 字符
    """
    now_ms = int(datetime.now(UTC).timestamp() * 1000)
    time_part = _encode_base62(now_ms, min_length=8)
    rand_part = ''.join(secrets.choice(_BASE62_ALPHABET) for _ in range(6))
    raw_uid = f'{time_part}{rand_part}'
    if prefix:
        clean_prefix = prefix.strip().rstrip('_')
        return f'{clean_prefix}_{raw_uid}'
    return raw_uid
