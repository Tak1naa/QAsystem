"""
关键信息提取器 —— 基于术语词典在问题文本中进行最长匹配。

从自然语言问题中提取6类实体：
  部件、故障或现象、工艺、指标、数值、单位
"""
from __future__ import annotations
import re
from typing import Any


NUMERIC_PATTERN = re.compile(
    r"(?<![\d.])(\d+(?:\.\d+)?)\s*(mm|毫米|μm|um|微米|MPa|兆帕|kPa|千帕|kN|千牛|mT|毫特|MΩ|兆欧|MQ|Ω|欧姆|"
    r"g·m|g\*m|克米|N·m|N\*m|牛米|牛·米|℃|°C|摄氏度|\%|％|百分比|min|分钟|h|小时)",
    re.I,
)

ENTITY_FIELDS = ["部件", "故障或现象", "工艺", "指标", "数值", "单位"]
SEMANTIC_FIELDS = ["部件", "故障或现象", "工艺", "指标"]


def extract(question: str, terms: dict[str, dict[str, list[str]]]) -> tuple[dict[str, list[dict[str, str]]], dict[str, list[dict[str, str]]]]:
    """
    从问题文本中提取实体，返回 (原始匹配, 标准化结果)。

    匹配策略：
      - 语义字段（部件/故障/工艺/指标）：术语词典最长匹配，同类不重叠
      - 数值/单位：正则提取

    Args:
        question: 用户原始问题文本
        terms: 术语词典，结构为 {类别: {标准名: [别名列表]}}

    Returns:
        (raw_entities, normalized_entities) —— 格式均为 {字段: [{原始词, 标准词}]}
    """
    raw = {field: [] for field in ENTITY_FIELDS}
    normalized = {field: [] for field in ENTITY_FIELDS}
    occupied: list[tuple[str, int, int]] = []

    # 语义字段：术语词典最长匹配
    for category in SEMANTIC_FIELDS:
        pairs: list[tuple[str, str]] = []
        for standard, aliases in terms.get(category, {}).items():
            for alias in aliases:
                if alias:
                    pairs.append((alias, standard))
        pairs.sort(key=lambda x: len(x[0]), reverse=True)

        for alias, standard in pairs:
            for match in re.finditer(re.escape(alias), question, flags=re.I):
                overlaps = any(
                    saved_category == category
                    and not (match.end() <= start or match.start() >= end)
                    for saved_category, start, end in occupied
                )
                if overlaps:
                    continue
                occupied.append((category, match.start(), match.end()))
                raw[category].append({"原始词": match.group(), "标准词": standard})
                normalized[category].append({"原始词": match.group(), "标准词": standard})

    # 数值/单位：正则提取
    for number, unit in NUMERIC_PATTERN.findall(question):
        raw["数值"].append({"原始词": number, "标准词": number})
        normalized["数值"].append({"原始词": number, "标准词": number})
        unit_std = next(
            (key for key, aliases in terms.get("单位", {}).items() if unit in aliases),
            unit,
        )
        raw["单位"].append({"原始词": unit, "标准词": unit_std})
        normalized["单位"].append({"原始词": unit, "标准词": unit_std})

    return raw, normalized
