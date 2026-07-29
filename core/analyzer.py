"""
规则引擎编排器 —— 串联分类→提取→完整性检查→路由，产出统一JSON。
analyze_with_rules(question) -> dict 是TEAM_PROTOCOL规定的唯一规则接口。
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from config import DATA_DIR
from core.schemas import ENTITY_FIELDS, empty_result
from core.classifier import classify
from core.extractor import extract
from core.completeness import check as check_completeness
from core.router import route as make_suggestion


def _load_terms() -> dict[str, dict[str, list[str]]]:
    with (Path(DATA_DIR) / "terminology.json").open(encoding="utf-8") as fh:
        return json.load(fh)


def analyze_with_rules(question: str) -> dict[str, Any]:
    """Stable offline baseline required by the shared interface."""
    started = time.perf_counter()

    # ---- Step 0: 初始化 ----
    result = empty_result(question, "rules")
    terms = _load_terms()

    # ---- Step 1: 实体提取 ----
    raw, normalized = extract(question, terms)

    # ---- Step 2: 问题分类 ----
    question_type, confidence = classify(question, normalized)

    # ---- Step 3: 完整性检查 ----
    completeness, missing, clarify_prompt = check_completeness(question_type, normalized)

    # ---- Step 4: 组装输出 ----
    result["问题类型"] = question_type
    result["已识别信息"] = raw
    result["标准化信息"] = normalized
    result["缺失信息"] = missing
    result["信息完整性"] = completeness
    result["澄清提示"] = clarify_prompt
    result["置信度"] = confidence

    # ---- Step 5: 处理建议 ----
    suggestion = make_suggestion(question_type, completeness, missing)
    result["处理建议"] = suggestion

    # ---- 元数据 ----
    elapsed = round((time.perf_counter() - started) * 1000, 2)
    result["运行耗时"] = {"规则耗时_ms": elapsed, "大模型耗时_ms": 0.0, "总耗时_ms": elapsed}
    result["元数据"] = {
        "fallback_used": False,
        "low_confidence": confidence < 0.65,
        "source": "rules",
    }
    return result
