from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # Keep the offline rules baseline runnable before dependency installation.
    def load_dotenv(*_args: object, **_kwargs: object) -> bool:
        return False

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
load_dotenv(PROJECT_ROOT / ".env")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip().rstrip("/")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash").strip()
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "20"))

QUESTION_TYPES = [
    "标准限度问题",
    "故障诊断问题",
    "工艺流程问题",
    "超限处置问题",
    "条件判断问题",
    "部件信息问题",
    "概念解释问题",
    "非动车检修问题",
]
ROUTE_LABELS = ["RAG", "KG", "CLARIFY", "OUT_OF_SCOPE"]
PROCESSING_MODES = ["rules", "llm", "hybrid"]
