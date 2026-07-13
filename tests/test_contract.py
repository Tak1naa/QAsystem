from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.schemas import ENTITY_FIELDS
from main import analyze


def test_rules_contract_is_complete() -> None:
    result = analyze("车轴划伤深度超过1mm怎么处理？", "rules")
    assert result["问题类型"] == "超限处置问题"
    assert result["处理建议"]["标签"] == "RAG"
    assert set(result["已识别信息"]) == set(ENTITY_FIELDS)
    assert set(result["标准化信息"]) == set(ENTITY_FIELDS)


def test_llm_failure_falls_back_to_rules() -> None:
    result = analyze("这个超了怎么办？", "llm")
    assert result["处理建议"]["标签"] == "CLARIFY"
    assert result["元数据"]["fallback_used"] is True

