from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from config import DATA_DIR
from core.schemas import ENTITY_FIELDS, empty_result

NUMERIC_PATTERN = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)\s*(mm|毫米|μm|um|微米|MPa|兆帕|kN|千牛|mT|毫特|℃|°C|%|％)", re.I)


def _load_terms() -> dict[str, dict[str, list[str]]]:
    with (Path(DATA_DIR) / "terminology.json").open(encoding="utf-8") as fh:
        return json.load(fh)


def _find_entities(question: str, terms: dict[str, dict[str, list[str]]]) -> tuple[dict[str, list[dict[str, str]]], dict[str, list[dict[str, str]]]]:
    raw = {field: [] for field in ENTITY_FIELDS}
    normalized = {field: [] for field in ENTITY_FIELDS}
    occupied: list[tuple[str, int, int]] = []
    for category in ENTITY_FIELDS:
        for standard, aliases in terms.get(category, {}).items():
            for alias in sorted(aliases, key=len, reverse=True):
                for match in re.finditer(re.escape(alias), question, flags=re.I):
                    # Longest aliases are visited first: do not also emit a shorter
                    # alias contained in an already accepted match of this category.
                    overlaps = any(
                        saved_category == category and not (match.end() <= start or match.start() >= end)
                        for saved_category, start, end in occupied
                    )
                    if overlaps:
                        continue
                    occupied.append((category, match.start(), match.end()))
                    raw[category].append({"原始词": match.group(), "标准词": standard})
                    normalized[category].append({"原始词": match.group(), "标准词": standard})
    for number, unit in NUMERIC_PATTERN.findall(question):
        raw["数值"].append({"原始词": number, "标准词": number})
        normalized["数值"].append({"原始词": number, "标准词": number})
        unit_standard = next((key for key, aliases in terms.get("单位", {}).items() if unit in aliases), unit)
        raw["单位"].append({"原始词": unit, "标准词": unit_standard})
        normalized["单位"].append({"原始词": unit, "标准词": unit_standard})
    return raw, normalized


def _classify(question: str, entities: dict[str, list[dict[str, str]]]) -> str:
    explicit_over_limit = any(word in question for word in ("超限", "超标", "超了", "超过", "过大"))
    if explicit_over_limit:
        return "超限处置问题"
    if not any(entities[field] for field in ("部件", "故障或现象", "工艺", "指标")):
        return "非动车检修问题"
    if entities["工艺"] or any(word in question for word in ("如何", "步骤", "流程", "怎么做")):
        return "工艺流程问题"
    if entities["指标"] and any(word in question for word in ("多少", "不超过", "小于", "标准", "限度")):
        return "标准限度问题"
    return "故障诊断问题"


def _requirements(question_type: str) -> list[str]:
    return {
        "标准限度问题": ["指标"],
        "故障诊断问题": ["部件", "故障或现象"],
        "工艺流程问题": ["工艺或部件"],
        "超限处置问题": ["具体部件", "超限指标"],
        "非动车检修问题": [],
    }[question_type]


def _missing(question_type: str, entities: dict[str, list[dict[str, str]]]) -> list[str]:
    checks = {
        "指标": bool(entities["指标"]),
        "部件": bool(entities["部件"]),
        "故障或现象": bool(entities["故障或现象"]),
        "工艺或部件": bool(entities["工艺"] or entities["部件"]),
        "具体部件": bool(entities["部件"]),
        "超限指标": bool(entities["指标"]),
    }
    return [field for field in _requirements(question_type) if not checks[field]]


def analyze_with_rules(question: str) -> dict[str, Any]:
    """Stable offline baseline required by the shared interface."""
    started = time.perf_counter()
    result = empty_result(question, "rules")
    raw, normalized = _find_entities(question, _load_terms())
    question_type = _classify(question, normalized)
    missing = _missing(question_type, normalized)
    result.update({"问题类型": question_type, "已识别信息": raw, "标准化信息": normalized, "缺失信息": missing})

    if question_type == "非动车检修问题":
        result["信息完整性"] = "非本领域问题"
        result["处理建议"] = {"标签": "OUT_OF_SCOPE", "理由": "未识别到动车检修范围内的部件、工艺、指标或故障术语。"}
        result["置信度"] = 0.85
    elif missing:
        result["信息完整性"] = "信息不足"
        result["澄清提示"] = f"以上问题信息不全，请补充{'、'.join(missing)}。"
        result["处理建议"] = {"标签": "CLARIFY", "理由": "当前问题缺少完成判断所需的关键信息。"}
        result["置信度"] = 0.45
    else:
        result["信息完整性"] = "完整"
        label = "KG" if question_type == "故障诊断问题" else "RAG"
        result["处理建议"] = {"标签": label, "理由": "问题信息完整，可进入后续知识查询模块。"}
        matched_categories = sum(bool(normalized[field]) for field in ("部件", "故障或现象", "工艺", "指标"))
        result["置信度"] = min(0.95, 0.60 + 0.10 * matched_categories)

    elapsed = round((time.perf_counter() - started) * 1000, 2)
    result["运行耗时"] = {"规则耗时_ms": elapsed, "大模型耗时_ms": 0.0, "总耗时_ms": elapsed}
    result["元数据"] = {"fallback_used": False, "low_confidence": result["置信度"] < 0.65, "source": "rules"}
    return result
