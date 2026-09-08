"""规则流水线，保持与页面和批量评估共用的输出格式。"""
from __future__ import annotations

import time
from typing import Any

from core.terminology import load_terms
from core.schemas import empty_result
from core.classifier import classify
from core.extractor import extract
from core.completeness import check
from core.router import route


def analyze_with_rules(question: str) -> dict[str, Any]:
    started = time.perf_counter()
    terms = load_terms()
    loaded = time.perf_counter()
    raw, normalized = extract(question, terms)
    extracted = time.perf_counter()
    question_type, confidence = classify(question, normalized)
    classified = time.perf_counter()
    completeness, missing, prompt = check(question_type, normalized, question)
    checked = time.perf_counter()
    suggestion = route(question_type, completeness, missing)
    finished = time.perf_counter()

    result = empty_result(question, "rules")
    result.update({
        "问题类型": question_type, "已识别信息": raw, "标准化信息": normalized,
        "缺失信息": missing, "信息完整性": completeness, "澄清提示": prompt,
        "置信度": confidence, "处理建议": suggestion,
    })
    elapsed = round((finished - started) * 1000, 4)
    result["运行耗时"] = {"规则耗时_ms": elapsed, "大模型耗时_ms": 0.0, "总耗时_ms": elapsed}
    result["元数据"] = {
        "fallback_used": False, "low_confidence": confidence < 0.65, "source": "rules",
        "阶段耗时_ms": {
            "词典加载": round((loaded - started) * 1000, 4),
            "提取与归一化": round((extracted - loaded) * 1000, 4),
            "分类": round((classified - extracted) * 1000, 4),
            "完整性": round((checked - classified) * 1000, 4),
            "路由": round((finished - checked) * 1000, 4),
        },
    }
    return result
