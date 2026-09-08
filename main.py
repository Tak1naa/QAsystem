from __future__ import annotations

import time
from typing import Literal

from config import PROCESSING_MODES
from core.analyzer import analyze_with_rules
from core.llm_client import analyze_with_llm

Mode = Literal["rules", "llm", "hybrid"]


def analyze(question: str, mode: Mode = "hybrid") -> dict:
    """Single integration point for the UI and evaluation modules."""
    if not question or not question.strip():
        raise ValueError("请输入问题")
    if mode not in PROCESSING_MODES:
        raise ValueError(f"不支持的处理模式：{mode}；可选值为 {', '.join(PROCESSING_MODES)}")
    started = time.perf_counter()
    rules = analyze_with_rules(question.strip())
    if mode == "rules":
        return rules

    should_call_llm = mode == "llm" or rules["元数据"]["low_confidence"]
    if not should_call_llm:
        rules["处理模式"] = "hybrid"
        rules["元数据"]["source"] = "rules_high_confidence"
        return rules

    llm_started = time.perf_counter()
    try:
        llm_result, _ = analyze_with_llm(question.strip())
        llm_result["运行耗时"]["规则耗时_ms"] = rules["运行耗时"]["规则耗时_ms"]
        llm_result["运行耗时"]["总耗时_ms"] = round((time.perf_counter() - started) * 1000, 3)
        if mode == "hybrid":
            llm_result["处理模式"] = "hybrid"
            llm_result["元数据"]["source"] = "rules_then_llm"
        return llm_result
    except RuntimeError as exc:
        rules["处理模式"] = mode
        rules["元数据"]["fallback_used"] = True
        rules["元数据"]["fallback_reason"] = str(exc)
        rules["元数据"]["source"] = "rules_fallback"
        rules["运行耗时"]["大模型耗时_ms"] = round((time.perf_counter() - llm_started) * 1000, 3)
        rules["运行耗时"]["总耗时_ms"] = round((time.perf_counter() - started) * 1000, 2)
        return rules


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="分析动车检修问题")
    parser.add_argument("text", nargs="*", help="检修问题（也可用 --question）")
    parser.add_argument("--question", help="检修问题")
    parser.add_argument("--mode", choices=PROCESSING_MODES, default="hybrid")
    args = parser.parse_args()
    if args.question is not None and args.text:
        parser.error("位置参数和 --question 只能选择一种")
    question = args.question if args.question is not None else " ".join(args.text) or "轴箱有点响，应该怎么办？"
    try:
        result = analyze(question, args.mode)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
