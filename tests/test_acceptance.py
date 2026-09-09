"""验收课程示例、术语来源覆盖及评估报告，不使用在线密钥。"""
import json
from pathlib import Path

import pytest

from config import QUESTION_TYPES, ROUTE_LABELS
from core.terminology import load_terms
from core.normalizer import TermNormalizer
from core import llm_client
from main import analyze
from evaluation.evaluate import compare_modes

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("question, tag", [
    ("轴箱有点响，可能是哪的问题？", "KG"),
    ("剩磁量不大于多少？", "RAG"),
    ("这个超了怎么办？", "CLARIFY"),
    ("今天北京天气怎么样？", "OUT_OF_SCOPE"),
])
def test_course_examples(question, tag):
    assert analyze(question, "rules")["处理建议"]["标签"] == tag


def test_terminology_source_coverage():
    terms = load_terms()
    TermNormalizer(terms)  # 同类别别名冲突必须在验收时失败。
    records = json.loads((ROOT / "data/terminology_sources.json").read_text(encoding="utf-8"))["术语"]
    expected = {(category, word) for category, words in terms.items() for word in words}
    actual = [(r["类别"], r["标准术语"]) for r in records]
    assert len(actual) == len(set(actual))
    assert set(actual) == expected
    for record in records:
        if record.get("PDF页码"):
            assert 1 <= record["PDF页码"] <= 52
            assert record["印刷页码"] == record["PDF页码"] + 23
            assert record["原文摘录"] and record["章节"]
        else:
            assert record.get("扩展理由")


@pytest.mark.parametrize("filename", ["questions.json", "questions_regression.json"])
def test_sample_labels(filename):
    samples = json.loads((ROOT / "data" / filename).read_text(encoding="utf-8"))
    terms = load_terms()
    assert len(samples) >= 20
    assert len({s["id"] for s in samples}) == len(samples)
    assert len({s["问题类型"] for s in samples}) >= 4
    for sample in samples:
        assert sample["问题类型"] in QUESTION_TYPES
        assert sample["处理标签"] in ROUTE_LABELS
        assert sample["原始问题"].strip()
        for field, words in sample["关键信息"].items():
            if field != "数值":
                assert set(words) <= terms[field].keys()


def test_three_mode_report_keeps_failures_and_provenance(monkeypatch, tmp_path):
    monkeypatch.setattr(llm_client, "DEEPSEEK_API_KEY", "")
    samples = json.loads((ROOT / "data/questions_regression.json").read_text(encoding="utf-8"))[:2]
    report = compare_modes(samples=samples, output_dir=tmp_path)
    assert len(report["metadata"]["samples_sha256"]) == 64
    assert report["summary"]["llm"]["source_counts"] == {"rules_fallback": 2}
    for mode in ("rules", "llm", "hybrid"):
        saved = json.loads((tmp_path / f"report_{mode}.json").read_text(encoding="utf-8"))
        assert saved["stats"]["completeness_correct"] == 2
        assert saved["stats"]["prompt_coverage_correct"] == 2
        assert (tmp_path / f"results_{mode}.csv").is_file()

