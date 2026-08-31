import os
import tomllib

from functools import lru_cache
from typing import TYPE_CHECKING

from backend.core.path import ROOT_DIR

if TYPE_CHECKING:
    from pathlib import Path


@lru_cache
def get_project_version() -> str:
    """从 pyproject.toml 读取项目发布版本号."""
    try:
        pyproject_path = ROOT_DIR / 'pyproject.toml'
        if pyproject_path.exists():
            with pyproject_path.open('rb') as f:
                data = tomllib.load(f)
                return str(data.get('project', {}).get('version', '0.0.0'))
    except OSError, tomllib.TOMLDecodeError:
        pass
    return '0.0.0'


def get_env_files() -> list[Path]:
    """计算按优先级覆盖的 .env 文件列表.

    优先级（后者覆盖前者）：
    1. .env
    2. .env.local
    3. .env.{ENVIRONMENT}
    4. .env.{ENVIRONMENT}.local
    5. 操作系统环境变量（最高优先级）
    """
    env = os.getenv('ENVIRONMENT')
    if not env:
        env_file = ROOT_DIR / '.env'
        if env_file.exists():
            for line in env_file.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if line.startswith('ENVIRONMENT='):
                    env = line.split('=', 1)[1].strip().strip('"\'')
                    break
    env = env or 'development'
    return [
        ROOT_DIR / '.env',
        ROOT_DIR / '.env.local',
        ROOT_DIR / f'.env.{env}',
        ROOT_DIR / f'.env.{env}.local',
    ]
