# evaluate.py - 动车检修问答系统批量评估程序
from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import analyze

ROOT = Path(__file__).resolve().parents[1]


def normalized_terms(result: dict, field: str) -> set[str]:
    """从标准化信息中提取指定字段的标准词集合"""
    return {item["标准词"] for item in result["标准化信息"].get(field, [])}


def load_samples() -> List[Dict]:
    """加载样本数据"""
    samples_path = ROOT / "data" / "questions.json"
    if not samples_path.exists():
        samples_path = ROOT / "questions.json"
    
    if not samples_path.exists():
        print(f"❌ 未找到样本文件: {samples_path}")
        sys.exit(1)
    
    return json.loads(samples_path.read_text(encoding="utf-8"))


def run_single_mode(mode: str = "rules") -> tuple[List[Dict], Dict]:
    """
    运行单个模式的评估
    
    Args:
        mode: "rules" | "llm" | "hybrid"
    
    Returns:
        (rows, stats): 详细结果列表和统计信息
    """
    samples = load_samples()
    rows = []
    
    print(f"\n>>> 正在运行模式: {mode.upper()}")
    print(f"   样本数: {len(samples)}")
    
    for idx, sample in enumerate(samples, 1):
        question = sample.get("原始问题", "")
        if not question:
            continue
        
        if idx % 10 == 0:
            print(f"   处理中... {idx}/{len(samples)}")
        
        start_time = time.time()
        try:
            result = analyze(question, mode)
        except Exception as e:
            print(f"   ⚠️ 问题 '{question[:20]}...' 分析失败: {e}")
            rows.append({
                "id": sample.get("id", f"ERR_{idx}"),
                "问题": question[:30] + "..." if len(question) > 30 else question,
                "模式": mode,
                "类型正确": False,
                "关键信息正确": False,
                "缺失判断正确": False,
                "路由正确": False,
                "总耗时_ms": 0,
                "规则耗时_ms": 0,
                "大模型耗时_ms": 0,
                "fallback": True,
            })
            continue
        
        elapsed = (time.time() - start_time) * 1000
        
        expected = sample.get("关键信息", {})
        expected_type = sample.get("问题类型", "")
        expected_missing = set(sample.get("缺失信息", []))
        expected_suggestion = sample.get("处理标签", "")
        
        # 判断各维度正确性
        type_ok = result["问题类型"] == expected_type
        
        # 关键信息正确：所有期望的标准词都在结果中
        entity_ok = True
        for field, values in expected.items():
            if not values:
                continue
            norm_set = normalized_terms(result, field)
            if not set(values).issubset(norm_set):
                entity_ok = False
                break
        
        missing_ok = set(result["缺失信息"]) == expected_missing
        route_ok = result["处理建议"]["标签"] == expected_suggestion
        
        rows.append({
            "id": sample.get("id", ""),
            "问题": question[:30] + "..." if len(question) > 30 else question,
            "模式": mode,
            "类型正确": type_ok,
            "关键信息正确": entity_ok,
            "缺失判断正确": missing_ok,
            "路由正确": route_ok,
            "总耗时_ms": round(elapsed, 2),
            "规则耗时_ms": result["运行耗时"].get("规则耗时_ms", 0),
            "大模型耗时_ms": result["运行耗时"].get("大模型耗时_ms", 0),
            "fallback": result["元数据"].get("fallback_used", False),
            # 用于错误分析
            "原始问题": question,
            "实际类型": result["问题类型"],
            "期望类型": expected_type,
            "实际路由": result["处理建议"]["标签"],
            "期望路由": expected_suggestion,
            "实际缺失": "|".join(result["缺失信息"]),
            "期望缺失": "|".join(expected_missing),
        })
    
    # 计算统计信息
    total = len(rows)
    valid_rows = [r for r in rows if r["总耗时_ms"] > 0 or r["fallback"]]
    valid_total = len(valid_rows) if valid_rows else 1
    
    stats = {
        "total": total,
        "valid": len(valid_rows),
        "type_correct": sum(r["类型正确"] for r in valid_rows),
        "entity_correct": sum(r["关键信息正确"] for r in valid_rows),
        "missing_correct": sum(r["缺失判断正确"] for r in valid_rows),
        "route_correct": sum(r["路由正确"] for r in valid_rows),
        "avg_time": sum(r["总耗时_ms"] for r in valid_rows) / valid_total if valid_rows else 0,
        "fallback_count": sum(r["fallback"] for r in rows),
    }
    
    return rows, stats


def save_csv(rows: List[Dict], output_path: Path) -> None:
    """保存CSV结果"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    fieldnames = [
        "id", "问题", "模式", "类型正确", "关键信息正确", 
        "缺失判断正确", "路由正确", "总耗时_ms", "规则耗时_ms", 
        "大模型耗时_ms", "fallback"
    ]
    
    with output_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def print_stats(mode: str, stats: Dict) -> None:
    """打印统计信息"""
    total = stats["valid"]
    if total == 0:
        print(f"   ⚠️ 无有效结果")
        return
    
    print(f"   ✅ 有效样本: {total}/{stats['total']}")
    print(f"   📊 类型识别准确率: {stats['type_correct']/total:.1%}")
    print(f"   📊 关键信息提取准确率: {stats['entity_correct']/total:.1%}")
    print(f"   📊 缺失判断准确率: {stats['missing_correct']/total:.1%}")
    print(f"   📊 路由建议准确率: {stats['route_correct']/total:.1%}")
    print(f"   ⏱️  平均耗时: {stats['avg_time']:.2f}ms")
    if stats.get("fallback_count", 0) > 0:
        print(f"   🔄 降级次数: {stats['fallback_count']}")


def compare_modes() -> None:
    """运行三种模式并对比结果"""
    modes = ["rules", "llm", "hybrid"]
    mode_names = {
        "rules": "纯规则引擎",
        "llm": "纯LLM (DeepSeek)",
        "hybrid": "混合模式 (规则+LLM)"
    }
    
    all_results = {}
    all_stats = {}
    
    print("=" * 70)
    print("🚄 动车检修问答系统 - 三模式批量评估")
    print("=" * 70)
    
    # 检查样本
    samples = load_samples()
    print(f"\n📁 加载样本: {len(samples)} 条")
    
    # 统计样本类型分布
    type_dist = defaultdict(int)
    for s in samples:
        type_dist[s.get("问题类型", "未知")] += 1
    print("   类型分布:")
    for t, c in sorted(type_dist.items()):
        print(f"      {t}: {c}条")
    
    # 运行各模式
    for mode in modes:
        print("\n" + "-" * 70)
        print(f"模式: {mode_names[mode]}")
        print("-" * 40)
        
        rows, stats = run_single_mode(mode)
        all_results[mode] = rows
        all_stats[mode] = stats
        
        # 保存CSV
        output_dir = ROOT / "evaluation"
        output_path = output_dir / f"results_{mode}.csv"
        save_csv(rows, output_path)
        print(f"   💾 已保存: {output_path}")
        print_stats(mode, stats)
    
    # ===== 生成对比报告 =====
    print("\n" + "=" * 70)
    print("📊 三模式对比汇总")
    print("=" * 70)
    
    print(f"\n{'指标':<22} {'规则引擎':<18} {'纯LLM':<18} {'混合模式':<18}")
    print("-" * 76)
    
    metrics = [
        ("类型识别准确率", "type_correct"),
        ("关键信息提取准确率", "entity_correct"),
        ("缺失判断准确率", "missing_correct"),
        ("路由建议准确率", "route_correct"),
    ]
    
    summary = {}
    for mode, stats in all_stats.items():
        total = stats["valid"]
        summary[mode] = {
            "total": total,
            "avg_time": stats["avg_time"],
            "type_acc": stats["type_correct"] / total if total else 0,
            "entity_acc": stats["entity_correct"] / total if total else 0,
            "missing_acc": stats["missing_correct"] / total if total else 0,
            "route_acc": stats["route_correct"] / total if total else 0,
            "fallback_count": stats.get("fallback_count", 0),
        }
    
    for label, key in metrics:
        values = [f"{summary[m][key]:>8.1%}" for m in modes]
        print(f"{label:<22} {values[0]:<18} {values[1]:<18} {values[2]:<18}")
    
    times = [f"{summary[m]['avg_time']:>8.2f}ms" for m in modes]
    print(f"{'平均耗时':<22} {times[0]:<18} {times[1]:<18} {times[2]:<18}")
    
    fallbacks = [f"{summary[m]['fallback_count']:>8}次" for m in modes]
    print(f"{'降级次数':<22} {fallbacks[0]:<18} {fallbacks[1]:<18} {fallbacks[2]:<18}")
    
    # ===== 错误案例分析 =====
    print("\n" + "=" * 70)
    print("🔍 错误案例分析（混合模式）")
    print("=" * 70)
    
    hybrid_rows = all_results.get("hybrid", [])
    error_rows = [
        r for r in hybrid_rows 
        if not all([r["类型正确"], r["关键信息正确"], r["缺失判断正确"], r["路由正确"]])
    ]
    
    if error_rows:
        print(f"\n共发现 {len(error_rows)} 个错误案例，显示前5个：")
        for i, err in enumerate(error_rows[:5], 1):
            print(f"\n📌 案例 {i}: {err.get('原始问题', err.get('问题', ''))}")
            print(f"   ❌ 期望: 类型={err.get('期望类型', '')}, 路由={err.get('期望路由', '')}, 缺失={err.get('期望缺失', '')}")
            print(f"   ✅ 实际: 类型={err.get('实际类型', '')}, 路由={err.get('实际路由', '')}, 缺失={err.get('实际缺失', '')}")
            error_items = []
            if not err["类型正确"]: error_items.append("类型识别")
            if not err["关键信息正确"]: error_items.append("关键信息提取")
            if not err["缺失判断正确"]: error_items.append("缺失判断")
            if not err["路由正确"]: error_items.append("路由建议")
            print(f"   🔴 错误项: {' → '.join(error_items)}")
    else:
        print("\n🎉 混合模式下无错误案例！")
    
    # ===== 保存报告 =====
    report = {
        "sample_count": len(samples),
        "type_distribution": dict(type_dist),
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
    
    report_path = ROOT / "evaluation" / "comparison_report.json"
    with report_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    print(f"\n📄 详细报告已保存: {report_path}")
    
    print("\n" + "=" * 70)
    print("✅ 评估完成！")
    print("=" * 70)


def print_usage() -> None:
    """打印使用说明"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║              动车检修问答系统 - 评估工具                      ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  使用方法:                                                   ║
║    python evaluate.py              # 运行三种模式并对比       ║
║    python evaluate.py rules        # 只运行规则模式           ║
║    python evaluate.py llm          # 只运行LLM模式            ║
║    python evaluate.py hybrid       # 只运行混合模式           ║
║                                                              ║
║  输出目录:                                                   ║
║    evaluation/results_{mode}.csv   # 详细结果                ║
║    evaluation/comparison_report.json # 对比报告               ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")


def main() -> None:
    """主函数"""
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode in ["rules", "llm", "hybrid"]:
            print("=" * 70)
            print(f"🚄 动车检修问答系统 - {mode.upper()} 模式评估")
            print("=" * 70)
            
            rows, stats = run_single_mode(mode)
            
            output_dir = ROOT / "evaluation"
            output_path = output_dir / f"results_{mode}.csv"
            save_csv(rows, output_path)
            
            print(f"\n💾 已保存: {output_path}")
            print_stats(mode, stats)
        else:
            print_usage()
    else:
        compare_modes()


if __name__ == "__main__":
    main()
