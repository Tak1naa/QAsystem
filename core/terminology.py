"""加载本地词典；修改词典后自动失效缓存。"""
import json
from functools import lru_cache
from pathlib import Path

from config import DATA_DIR


@lru_cache(maxsize=4)
def _read(path: str, modified_ns: int) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_terms() -> dict:
    path = Path(DATA_DIR) / "terminology.json"
    return _read(str(path), path.stat().st_mtime_ns)
