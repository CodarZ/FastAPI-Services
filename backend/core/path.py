from pathlib import Path

# 项目根目录
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# 源码根目录（backend/）
BACKEND_DIR = ROOT_DIR / 'backend'

# 日志输出目录
LOG_DIR = ROOT_DIR / 'logs'

# 环境变量文件路径
ENV_FILE_PATH = ROOT_DIR / '.env'

# Alembic 数据库迁移版本脚本目录
ALEMBIC_VERSION_DIR = BACKEND_DIR / 'migrations' / 'versions'

# 静态资源目录
STATIC_DIR = ROOT_DIR / 'static'
# IP 属地离线数据文件路径
IP2REGION_XDB_PATH = STATIC_DIR / 'ip2region.xdb'

# 确保目录存在
for directory in (LOG_DIR, STATIC_DIR):
    directory.mkdir(parents=True, exist_ok=True)
