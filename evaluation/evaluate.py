from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import analyze

ROOT = Path(__file__).resolve().parents[1]


def normalized_terms(result: dict, field: str) -> set[str]:
    return {item["标准词"] for item in result["标准化信息"].get(field, [])}


def run(mode: str = "rules") -> list[dict]:
    samples = json.loads((ROOT / "data" / "questions.json").read_text(encoding="utf-8"))
    rows = []
    for sample in samples:
        result = analyze(sample["原始问题"], mode)
        expected = sample.get("关键信息", {})
        entity_ok = all(set(values).issubset(normalized_terms(result, field)) for field, values in expected.items())
        rows.append({
            "id": sample["id"], "问题": sample["原始问题"], "模式": mode,
            "类型正确": result["问题类型"] == sample["问题类型"],
            "关键信息正确": entity_ok,
            "缺失判断正确": set(result["缺失信息"]) == set(sample.get("缺失信息", [])),
            "路由正确": result["处理建议"]["标签"] == sample["处理标签"],
            "总耗时_ms": result["运行耗时"]["总耗时_ms"],
            "fallback": result["元数据"].get("fallback_used", False),
        })
    return rows


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "rules"
    rows = run(mode)
    output = ROOT / "evaluation" / "results.csv"
    with output.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=rows[0].keys())
        writer.writeheader(); writer.writerows(rows)
    total = len(rows)
    print(f"已生成 {output}")
    for key in ("类型正确", "关键信息正确", "缺失判断正确", "路由正确"):
        print(f"{key}: {sum(row[key] for row in rows) / total:.1%}")

