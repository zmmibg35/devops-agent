"""
测试配置：将项目根目录加入 sys.path，使 clients/tools 可被直接导入。
"""

import sys
from pathlib import Path

# 将项目根目录加入 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))
