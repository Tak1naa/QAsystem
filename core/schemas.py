from __future__ import annotations

from typing import Any

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

    missing = payload.get("缺失信息")
    if not isinstance(missing, list) or not all(isinstance(item, str) for item in missing):
        raise ValueError("缺失信息必须是字符串数组")
    result["缺失信息"] = missing
    result["信息完整性"] = str(payload.get("信息完整性", "信息不足"))
    clarification = payload.get("澄清提示")
    if not isinstance(clarification, str):
        raise ValueError("澄清提示必须是字符串")
    result["澄清提示"] = clarification

    route = payload.get("处理建议", {})
    if not isinstance(route, dict) or route.get("标签") not in ROUTE_LABELS:
        raise ValueError("模型输出的处理建议标签不合法")
    result["处理建议"] = {"标签": route["标签"], "理由": str(route.get("理由", ""))}

    confidence = payload.get("置信度", 0.5)
    try:
        result["置信度"] = max(0.0, min(1.0, float(confidence)))
    except (TypeError, ValueError):
        result["置信度"] = 0.5
    return result
