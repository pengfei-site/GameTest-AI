
import os
from pathlib import Path
from dotenv import load_dotenv

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 加载项目根目录下的 .env
load_dotenv(BASE_DIR / ".env")

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv(
    "DEEPSEEK_BASE_URL",
    "https://api.deepseek.com"
)
DEEPSEEK_MODEL = os.getenv(
    "DEEPSEEK_MODEL",
    "deepseek-flash"
)

def validate_ai_config():
    """检查 AI 配置是否完整"""
    if not DEEPSEEK_API_KEY:
        raise ValueError(
            "未配置 DEEPSEEK_API_KEY，请检查项目根目录下的 .env 文件"
        )

    return True
