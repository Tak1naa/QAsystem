from __future__ import annotations

from typing import Any
import math

from config import QUESTION_TYPES, ROUTE_LABELS

ENTITY_FIELDS = ["部件", "故障或现象", "工艺", "指标", "数值", "单位"]


def empty_entities() -> dict[str, list[dict[str, str]]]:
    return {field: [] for field in ENTITY_FIELDS}


def empty_result(question: str, mode: str) -> dict[str, Any]:
    return {
        "原始问题": question,
        "问题类型": "",
        "已识别信息": empty_entities(),
        "标准化信息": empty_entities(),
        "缺失信息": [],
        "信息完整性": "",
        "澄清提示": "",
        "处理建议": {"标签": "", "理由": ""},
        "置信度": 0.0,
        "处理模式": mode,
        "运行耗时": {"规则耗时_ms": 0.0, "大模型耗时_ms": 0.0, "总耗时_ms": 0.0},
        "元数据": {"fallback_used": False, "low_confidence": False, "source": ""},
    }


def validate_result(payload: Any, question: str, mode: str) -> dict[str, Any]:
    """Normalize untrusted LLM output to the shared team contract."""
    result = empty_result(question, mode)
    if not isinstance(payload, dict):
        raise ValueError("模型输出不是 JSON 对象")

    result["问题类型"] = payload.get("问题类型", "")
    if result["问题类型"] not in QUESTION_TYPES:
        raise ValueError("模型输出的问题类型不在约定范围内")

    for key in ("已识别信息", "标准化信息"):
        if key not in payload:
            raise ValueError(f"模型输出缺少 {key}")
        source = payload[key]
        if not isinstance(source, dict):
            raise ValueError(f"{key} 必须是对象")
        for field in ENTITY_FIELDS:
            if field not in source:
                raise ValueError(f"模型输出缺少 {key}.{field}")
            values = source[field]
            if not isinstance(values, list):
                raise ValueError(f"{key}.{field} 必须是数组")
            if not all(isinstance(item, dict) and all(
                isinstance(item.get(name), str) and item[name].strip()
                for name in ("原始词", "标准词")
            ) for item in values):
                raise ValueError(f"{key}.{field} 的条目必须包含非空原始词和标准词")
            result[key][field] = values
            if any(item["原始词"].casefold() not in question.casefold() for item in values):
                raise ValueError(f"{key}.{field} 包含原文未出现的实体")

    missing = payload.get("缺失信息")
    if not isinstance(missing, list) or not all(isinstance(item, str) for item in missing):
        raise ValueError("缺失信息必须是字符串数组")
    result["缺失信息"] = missing
    result["信息完整性"] = str(payload.get("信息完整性", "信息不足"))
    if result["信息完整性"] not in ("完整", "信息不足", "非本领域问题"):
        raise ValueError("信息完整性枚举不合法")
    clarification = payload.get("澄清提示")
    if not isinstance(clarification, str):
        raise ValueError("澄清提示必须是字符串")
    result["澄清提示"] = clarification

    route = payload.get("处理建议", {})
    if not isinstance(route, dict) or route.get("标签") not in ROUTE_LABELS:
        raise ValueError("模型输出的处理建议标签不合法")
    result["处理建议"] = {"标签": route["标签"], "理由": str(route.get("理由", ""))}
    if not result["处理建议"]["理由"].strip():
        raise ValueError("处理建议必须包含理由")
    if missing and (route["标签"] != "CLARIFY" or result["信息完整性"] != "信息不足" or not clarification.strip()):
        raise ValueError("缺失信息、完整性、澄清提示和路由不一致")
    if not missing and (route["标签"] == "CLARIFY" or result["信息完整性"] == "信息不足"):
        raise ValueError("需要澄清时必须列出缺失信息")
    outside = result["问题类型"] == "非动车检修问题"
    if outside != (route["标签"] == "OUT_OF_SCOPE") or outside != (result["信息完整性"] == "非本领域问题"):
        raise ValueError("非领域分类与路由不一致")

    confidence = payload.get("置信度", 0.5)
    try:
        value = float(confidence)
        if isinstance(confidence, bool) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("置信度必须是0到1之间的有限数值")
        result["置信度"] = value
    except (TypeError, ValueError):
        raise ValueError("置信度必须是0到1之间的有限数值") from None
    return result
