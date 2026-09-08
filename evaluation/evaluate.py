"""批量评估公共接口，记录预测、错误案例和实际运行来源。"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from collections import defaultdict
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import analyze

ROOT = Path(__file__).resolve().parents[1]


def normalized_terms(result: dict, field: str) -> set[str]:
    """从标准化信息中提取指定字段的标准词集合"""
    return {item.get("标准词", "") for item in result.get("标准化信息", {}).get(field, []) if item.get("标准词")}


def load_samples() -> list[dict]:
    """加载样本数据"""
    samples_path = ROOT / "data" / "questions.json"
    if not samples_path.exists():
        samples_path = ROOT / "questions.json"
    
    if not samples_path.exists():
        print(f"错误: 未找到样本文件: {samples_path}")
        sys.exit(1)
    
    with samples_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def run_mode(mode: str = "hybrid", sample_limit: int | None = None, samples: list[dict] | None = None) -> tuple[list[dict], dict]:
    """
    运行指定模式的评估
    
    Args:
        mode: "rules" | "llm" | "hybrid"
        sample_limit: 限制样本数量（用于快速测试）
    
    Returns:
        (rows, stats)
    """
    samples = load_samples() if samples is None else samples
    if sample_limit is not None:
        if sample_limit <= 0:
            raise ValueError("样本数限制必须大于0")
        samples = samples[:sample_limit]
    
    rows = []
    
    print(f"\n>>> 运行模式: {mode.upper()} ({len(samples)} 条样本)")
    
    for idx, sample in enumerate(samples, 1):
        question = sample.get("原始问题", "")
        if not isinstance(question, str) or not question.strip():
            raise ValueError(f"样本{sample.get('id')}的原始问题为空")
        
        if idx % 20 == 0:
            print(f"   进度: {idx}/{len(samples)}")
        
        start_time = time.perf_counter()
        try:
            result = analyze(question, mode)
        except Exception as e:
            print(f"   警告: 问题 '{question[:20]}...' 失败: {e}")
            rows.append({
                "id": sample.get("id", f"ERR_{idx}"),
                "问题": question[:30] + "..." if len(question) > 30 else question,
                "模式": mode,
                "成功": False,
                "类型正确": False,
                "关键信息正确": False,
                "缺失判断正确": False,
                "路由正确": False,
                "总耗时_ms": round((time.perf_counter() - start_time) * 1000, 4),
                "错误": f"{type(e).__name__}: {e}",
                "实体标注完整": sample.get("实体标注完整", False),
                "实体TP": 0,
                "实体FP": 0,
                "实体FN": sum(len(set(v)) for v in sample.get("关键信息", {}).values()),
                "规则耗时_ms": 0,
                "大模型耗时_ms": 0,
                "fallback": False,
                "原始问题": question,
                "实际类型": "ERROR",
                "期望类型": sample.get("问题类型", ""),
                "实际路由": "ERROR",
                "期望路由": sample.get("处理标签", ""),
                "实际缺失": "ERROR",
                "期望缺失": "|".join(sample.get("缺失信息", [])),
            })
            continue
        
        elapsed = (time.perf_counter() - start_time) * 1000
        
        expected = sample.get("关键信息", {})
        expected_type = sample.get("问题类型", "")
        expected_missing = set(sample.get("缺失信息", []))
        expected_route = sample.get("处理标签", "")
        
        type_ok = result.get("问题类型", "") == expected_type
        
        expected_entities = {(field, value) for field, values in expected.items() for value in values}
        actual_entities = {(field, value) for field in result.get("标准化信息", {})
                           for value in normalized_terms(result, field)}
        full = sample.get("实体标注完整", False)
        entity_ok = actual_entities == expected_entities if full else expected_entities <= actual_entities
        
        actual_missing = set(result.get("缺失信息", []))
        missing_ok = actual_missing == expected_missing
        
        actual_route = result.get("处理建议", {}).get("标签", "")
        route_ok = actual_route == expected_route
        
        rows.append({
            "id": sample.get("id", ""),
            "问题": question[:30] + "..." if len(question) > 30 else question,
            "模式": mode,
            "成功": True,
            "实际来源": result.get("元数据", {}).get("source", "unknown"),
            "实际实体": result.get("标准化信息", {}),
            "期望实体": expected,
            "实体标注完整": full,
            "实体TP": len(actual_entities & expected_entities),
            "实体FP": len(actual_entities - expected_entities) if full else None,
            "实体FN": len(expected_entities - actual_entities),
            "漏提实体": sorted(expected_entities - actual_entities),
            "多提实体": sorted(actual_entities - expected_entities) if full else None,
            "澄清触发正确": bool(result.get("澄清提示", "").strip()) == bool(expected_missing),
            "类型正确": type_ok,
            "关键信息正确": entity_ok,
            "缺失判断正确": missing_ok,
            "路由正确": route_ok,
            "总耗时_ms": round(elapsed, 4),
            "规则耗时_ms": result.get("运行耗时", {}).get("规则耗时_ms", 0),
            "大模型耗时_ms": result.get("运行耗时", {}).get("大模型耗时_ms", 0),
            "fallback": result.get("元数据", {}).get("fallback_used", False),
            "原始问题": question,
            "实际类型": result.get("问题类型", ""),
            "期望类型": expected_type,
            "实际路由": actual_route,
            "期望路由": expected_route,
            "实际缺失": "|".join(sorted(actual_missing)),
            "期望缺失": "|".join(sorted(expected_missing)),
        })
    
    total = len(rows)
    # 成功与耗时无关：快速运行记录为0ms时也必须计入。
    valid = [r for r in rows if r["成功"]]
    vc = len(valid) if valid else 1
    
    stats = {
        "total": total,
        "valid": len(valid),
        "type_correct": sum(r["类型正确"] for r in valid),
        "entity_correct": sum(r["关键信息正确"] for r in valid),
        "missing_correct": sum(r["缺失判断正确"] for r in valid),
        "route_correct": sum(r["路由正确"] for r in valid),
        "avg_time": sum(r["总耗时_ms"] for r in valid) / vc if valid else 0,
        "fallback_count": sum(r["fallback"] for r in rows),
    }
    fully_annotated = [r for r in rows if r.get("实体标注完整")]
    stats["entity_micro"] = None
    if fully_annotated:
        tp = sum(r["实体TP"] for r in fully_annotated)
        fp = sum(r["实体FP"] for r in fully_annotated)
        fn = sum(r["实体FN"] for r in fully_annotated)
        stats["entity_micro"] = {
            "samples": len(fully_annotated), "tp": tp, "fp": fp, "fn": fn,
            "precision": tp / (tp + fp) if tp + fp else 0,
            "recall": tp / (tp + fn) if tp + fn else 0,
            "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0,
        }
    stats["clarification_correct"] = sum(r.get("澄清触发正确", False) for r in rows)
    return rows, stats


def save_csv(rows: list[dict], output_path: Path) -> None:
    """保存 CSV 结果"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    fieldnames = [
        "id", "问题", "模式", "类型正确", "关键信息正确",
        "缺失判断正确", "路由正确", "总耗时_ms", "规则耗时_ms",
        "大模型耗时_ms", "fallback", "成功", "实际来源", "实际类型", "期望类型",
        "实际路由", "期望路由", "实际缺失", "期望缺失", "实际实体", "期望实体", "澄清触发正确",
        "实体标注完整", "实体TP", "实体FP", "实体FN", "漏提实体", "多提实体", "错误"
    ]
    
    with output_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(row.get(k), ensure_ascii=False) if isinstance(row.get(k), (dict, list)) else row.get(k, "") for k in fieldnames})


def print_stats(stats: dict) -> None:
    """打印统计信息"""
    total = stats["total"]
    if total == 0:
        print("   警告: 无有效结果")
        return
    
    print(f"   成功样本: {stats['valid']}/{total}")
    print(f"   类型识别准确率: {stats['type_correct']/total:.1%}")
    print(f"   关键信息提取准确率: {stats['entity_correct']/total:.1%}")
    print(f"   缺失判断准确率: {stats['missing_correct']/total:.1%}")
    print(f"   路由建议准确率: {stats['route_correct']/total:.1%}")
    print(f"   平均耗时: {stats['avg_time']:.2f}ms")
    if stats.get("fallback_count", 0) > 0:
        print(f"   降级次数: {stats['fallback_count']}")


def compare_modes(sample_limit: int | None = None, samples: list[dict] | None = None, output_dir: Path | None = None) -> dict:
    """三模式对比"""
    output_dir = output_dir or ROOT / "evaluation"
    output_dir.mkdir(parents=True, exist_ok=True)
    modes = ["rules", "llm", "hybrid"]
    mode_names = {
        "rules": "纯规则引擎",
        "llm": "LLM优先（失败时规则回退）",
        "hybrid": "混合模式 (规则+LLM)"
    }
    
    all_results = {}
    all_stats = {}
    
    print("=" * 70)
    print("动车检修问答系统 - 三模式批量评估")
    print("=" * 70)
    
    samples = load_samples() if samples is None else samples
    if sample_limit is not None:
        if sample_limit <= 0:
            raise ValueError("样本数限制必须大于0")
        samples = samples[:sample_limit]
    print(f"\n加载样本: {len(samples)} 条")
    
    type_dist = defaultdict(int)
    for s in samples:
        type_dist[s.get("问题类型", "未知")] += 1
    print("   类型分布:")
    for t, c in sorted(type_dist.items()):
        print(f"      {t}: {c}条")
    
    for mode in modes:
        print("\n" + "-" * 70)
        print(f"模式: {mode_names[mode]}")
        print("-" * 40)
        
        rows, stats = run_mode(mode, samples=samples)
        all_results[mode] = rows
        all_stats[mode] = stats
        
        output_path = output_dir / f"results_{mode}.csv"
        save_csv(rows, output_path)
        print(f"   已保存: {output_path}")
        print_stats(stats)
    
    print("\n" + "=" * 70)
    print("三模式对比汇总")
    print("=" * 70)
    
    print(f"\n{'指标':<22} {'规则引擎':<18} {'纯LLM':<18} {'混合模式':<18}")
    print("-" * 76)
    
    metrics = [
        ("类型识别准确率", "type_acc"),
        ("关键信息提取准确率", "entity_acc"),
        ("缺失判断准确率", "missing_acc"),
        ("路由建议准确率", "route_acc"),
    ]
    
    summary = {}
    for mode, stats in all_stats.items():
        total = stats["total"]
        summary[mode] = {
            "total": total,
            "avg_time": stats["avg_time"],
            "type_acc": stats["type_correct"] / total if total else 0,
            "entity_acc": stats["entity_correct"] / total if total else 0,
            "missing_acc": stats["missing_correct"] / total if total else 0,
            "route_acc": stats["route_correct"] / total if total else 0,
            "fallback_count": stats.get("fallback_count", 0),
            "successful": stats["valid"],
            "entity_micro": stats["entity_micro"],
            "clarification_acc": stats["clarification_correct"] / total if total else 0,
        }
    
    for label, key in metrics:
        values = [f"{summary[m][key]:>8.1%}" for m in modes]
        print(f"{label:<22} {values[0]:<18} {values[1]:<18} {values[2]:<18}")
    
    times = [f"{summary[m]['avg_time']:>8.2f}ms" for m in modes]
    print(f"{'平均耗时':<22} {times[0]:<18} {times[1]:<18} {times[2]:<18}")
    
    fallbacks = [f"{summary[m]['fallback_count']:>8}次" for m in modes]
    print(f"{'降级次数':<22} {fallbacks[0]:<18} {fallbacks[1]:<18} {fallbacks[2]:<18}")
    
    print("\n" + "=" * 70)
    print("错误案例分析（混合模式）")
    print("=" * 70)
    
    hybrid_rows = all_results.get("hybrid", [])
    error_rows = [
        r for r in hybrid_rows
        if not all([r["类型正确"], r["关键信息正确"], r["缺失判断正确"], r["路由正确"]])
    ]
    
    if error_rows:
        print(f"\n共发现 {len(error_rows)} 个错误案例，显示前5个：")
        for i, err in enumerate(error_rows[:5], 1):
            print(f"\n案例 {i}: {err.get('原始问题', err.get('问题', ''))}")
            print(f"   期望: 类型={err.get('期望类型', '')}, 路由={err.get('期望路由', '')}, 缺失={err.get('期望缺失', '')}")
            print(f"   实际: 类型={err.get('实际类型', '')}, 路由={err.get('实际路由', '')}, 缺失={err.get('实际缺失', '')}")
            error_items = []
            if not err["类型正确"]: error_items.append("类型识别")
            if not err["关键信息正确"]: error_items.append("关键信息提取")
            if not err["缺失判断正确"]: error_items.append("缺失判断")
            if not err["路由正确"]: error_items.append("路由建议")
            print(f"   错误项: {' -> '.join(error_items)}")
    else:
        print("\n混合模式下无错误案例")
    
    report = {
        "sample_count": len(samples),
        "type_distribution": dict(type_dist),
        "results": all_results,
        "summary": summary,
        "error_count": len(error_rows),
        "errors": [
            {
                "id": e.get("id", ""),
                "question": e.get("原始问题", e.get("问题", "")),
                "expected": {
                    "type": e.get("期望类型", ""),
                    "route": e.get("期望路由", ""),
                    "missing": e.get("期望缺失", "")
                },
                "actual": {
                    "type": e.get("实际类型", ""),
                    "route": e.get("实际路由", ""),
                    "missing": e.get("实际缺失", "")
                }
            }
            for e in error_rows[:10]
        ]
    }
    
    report_path = output_dir / "comparison_report.json"
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n详细报告已保存: {report_path}")
    
    md_path = output_dir / "评估报告.md"
    generate_markdown(md_path, summary, modes, mode_names, error_rows)
    print(f"Markdown报告已保存: {md_path}")
    
    print("\n" + "=" * 70)
    print("评估完成")
    print("=" * 70)
    return report


def generate_markdown(md_path: Path, summary: dict, modes: list, mode_names: dict, errors: list) -> None:
    """生成 Markdown 报告"""
    lines = [
        "# 动车检修问答系统 - 评估报告",
        "",
        f"**生成时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 1. 三模式对比",
        "",
        "| 指标 | 规则引擎 | 纯LLM | 混合模式 |",
        "|------|----------|-------|----------|",
    ]
    
    metrics = [
        ("类型识别准确率", "type_acc"),
        ("关键信息提取准确率", "entity_acc"),
        ("缺失判断准确率", "missing_acc"),
        ("路由建议准确率", "route_acc"),
    ]
    
    for label, key in metrics:
        values = [f"{summary[m][key]:.1%}" for m in modes]
        lines.append(f"| {label} | {values[0]} | {values[1]} | {values[2]} |")
    
    times = [f"{summary[m]['avg_time']:.2f}ms" for m in modes]
    lines.append(f"| 平均耗时 | {times[0]} | {times[1]} | {times[2]} |")
    
    lines.extend([
        "",
        "## 2. 结论与建议",
        "",
        "- 全部样本参与准确率统计，执行失败计为错误。",
        f"- 规则模式本次平均耗时 {summary['rules']['avg_time']:.2f}ms。",
        "- LLM与混合模式必须结合实际来源和回退次数解读；回退结果不能作为在线模型性能证据。",
        "- 当前实体指标是预期实体覆盖率，不处罚额外提取项，不能称为实体精确率。",
        f"- 回退次数：LLM {summary['llm']['fallback_count']}，混合 {summary['hybrid']['fallback_count']}。",
        "",
        "## 3. 错误案例分析",
        "",
    ])
    
    if errors:
        lines.append(f"共发现 **{len(errors)}** 个错误案例：")
        lines.append("")
        for i, err in enumerate(errors[:5], 1):
            lines.append(f"### 案例 {i}")
            lines.append(f"- **问题**: {err.get('原始问题', err.get('问题', ''))}")
            lines.append(f"- **期望**: 类型={err.get('期望类型', '')}, 路由={err.get('期望路由', '')}")
            lines.append(f"- **实际**: 类型={err.get('实际类型', '')}, 路由={err.get('实际路由', '')}")
            lines.append("")
    else:
        lines.append("无错误案例")
    
    lines.append("---")
    lines.append("*报告由 evaluate.py 自动生成*")
    
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", nargs="?", default="rules", choices=("rules", "llm", "hybrid", "all"))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--samples", type=Path, default=ROOT / "data/questions.json")
    parser.add_argument("--output", type=Path, default=ROOT / "evaluation/latest")
    args = parser.parse_args()
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit 必须大于0")
    samples = json.loads(args.samples.read_text(encoding="utf-8"))
    if not isinstance(samples, list) or not samples:
        parser.error("样本必须是非空数组")
    if args.mode == "all":
        compare_modes(args.limit, samples, args.output)
        return
    rows, stats = run_mode(args.mode, args.limit, samples)
    save_csv(rows, args.output / f"results_{args.mode}.csv")
    (args.output / "report.json").write_text(json.dumps({"stats": stats, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    print_stats(stats)
    if stats["entity_micro"]:
        print("实体micro指标:", stats["entity_micro"])


if __name__ == "__main__":
    main()
