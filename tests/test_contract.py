from __future__ import annotations

import sys
import json
from unittest.mock import MagicMock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from core.schemas import ENTITY_FIELDS
from core import llm_client
from core.schemas import validate_result
from main import analyze


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(llm_client, "OPENAI_API_KEY", "")


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


@pytest.mark.parametrize("mode", ["rules", "llm", "hybrid"])
def test_all_modes_keep_the_same_contract(mode: str) -> None:
    expected_keys = {
        "原始问题", "问题类型", "已识别信息", "标准化信息", "缺失信息", "信息完整性",
        "澄清提示", "处理建议", "置信度", "处理模式", "运行耗时", "元数据",
    }
    result = analyze("这个超了怎么办？", mode)
    assert set(result) == expected_keys
    assert set(result["已识别信息"]) == set(ENTITY_FIELDS)
    assert set(result["标准化信息"]) == set(ENTITY_FIELDS)


def test_invalid_mode_is_rejected() -> None:
    with pytest.raises(ValueError, match="不支持的处理模式"):
        analyze("轴箱有点响", "unknown")  # type: ignore[arg-type]


@pytest.mark.parametrize("bad_body", [b"[]", b"not-json"])
def test_invalid_response_retries_then_succeeds(monkeypatch, bad_body):
    valid = analyze("今天北京天气怎么样？", "rules")
    response = MagicMock()
    response.__enter__.return_value.read.side_effect = [
        bad_body,
        json.dumps({"choices": [{"message": {"content": json.dumps(valid)}}]}).encode(),
    ]
    request = MagicMock(return_value=response)
    monkeypatch.setattr(llm_client, "OPENAI_API_KEY", "test-only")
    monkeypatch.setattr(llm_client, "urlopen", request)
    result = analyze("今天北京天气怎么样？", "llm")
    assert request.call_count == 2
    assert result["元数据"]["source"] == "llm"


def test_timeout_falls_back(monkeypatch):
    request = MagicMock(side_effect=TimeoutError())
    monkeypatch.setattr(llm_client, "OPENAI_API_KEY", "test-only")
    monkeypatch.setattr(llm_client, "urlopen", request)
    assert analyze("这个超了怎么办？", "llm")["元数据"]["fallback_used"]
    assert request.call_count == 2


def test_missing_entity_keys_rejected():
    result = analyze("车轴划伤深度超过1mm怎么处理？", "rules")
    result["已识别信息"]["部件"] = [{}]
    with pytest.raises(ValueError, match="原始词和标准词"):
        validate_result(result, result["原始问题"], "llm")
