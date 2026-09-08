"""覆盖评估口径、数值边界和页面转义，不依赖在线API。"""
import ast
import html
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from core.schemas import validate_result
from evaluation import evaluate
from main import analyze


@pytest.mark.parametrize("arguments", [
    ["--mode", "rules", "--question", "车轴如何检查？"],
    ["车轴如何检查？", "--mode", "rules"],
])
def test_cli_preserves_question_and_mode(arguments):
    completed = subprocess.run(
        [sys.executable, "-X", "utf8", "main.py", *arguments],
        cwd=Path(__file__).parents[1], capture_output=True, encoding="utf-8", check=True,
    )
    result = json.loads(completed.stdout)
    assert result["原始问题"] == "车轴如何检查？"
    assert result["处理模式"] == "rules"


def test_cli_rejects_invalid_mode():
    completed = subprocess.run(
        [sys.executable, "-X", "utf8", "main.py", "--mode", "invalid"],
        cwd=Path(__file__).parents[1], capture_output=True, encoding="utf-8",
    )
    assert completed.returncode == 2
    assert "invalid choice" in completed.stderr


@pytest.mark.parametrize("question, expected", [
    ("车轴的划伤深度超过多少需要修复？", "标准限度问题"),
    ("车轴的划伤深度超标，如何处置？", "超限处置问题"),
    ("轮对包括哪些部件？", "部件信息问题"),
    ("什么是磁粉探伤？", "概念解释问题"),
    ("车轮直径小于800mm是否报废？", "条件判断问题"),
])
def test_intent_boundaries(question, expected):
    assert analyze(question, "rules")["问题类型"] == expected


def test_unitless_measurement_is_retained():
    result = analyze("这个测出来0.3算正常吗？", "rules")
    assert result["标准化信息"]["数值"] == [{"原始词": "0.3", "标准词": "0.3"}]
    assert result["处理建议"]["标签"] == "CLARIFY"


def test_generic_names_are_not_narrowed():
    result = analyze("减振器和传感器如何检查？", "rules")
    assert {i["标准词"] for i in result["标准化信息"]["部件"]} == {"减振器", "传感器"}


def test_html_highlight_preserves_original_text():
    tree = ast.parse((Path(__file__).parents[1] / "app.py").read_text(encoding="utf-8"))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "highlight")
    namespace = {"html": html, "re": re, "HIGHLIGHT_COLORS": {}}
    exec(compile(ast.Module(body=[function], type_ignores=[]), "app.py", "exec"), namespace)
    question = '若 < 5mm & "车轮" 怎么办？'
    rendered = namespace["highlight"](question, {"部件": [{"原始词": "车轮"}]})
    assert '&lt; 5mm &amp; &quot;' in rendered
    assert '>车轮<small>' in rendered
    assert rendered.endswith('&quot; 怎么办？')


@pytest.mark.parametrize("confidence", [float("nan"), float("inf"), -1, 2, True])
def test_invalid_confidence_rejected(confidence):
    result = analyze("今天北京天气怎么样？", "rules")
    result["置信度"] = confidence
    with pytest.raises(ValueError, match="置信度"):
        validate_result(result, result["原始问题"], "llm")


def test_zero_duration_success_is_counted(monkeypatch):
    monkeypatch.setattr(evaluate.time, "perf_counter", lambda: 1.0)
    _, stats = evaluate.run_mode("rules", 2)
    assert stats["valid"] == stats["total"] == 2


def test_failed_sample_remains_in_denominator(monkeypatch):
    def fail(*args):
        raise RuntimeError("test error")
    monkeypatch.setattr(evaluate, "analyze", fail)
    rows, stats = evaluate.run_mode("rules", 2)
    assert stats["total"] == 2 and stats["valid"] == 0
    assert len(rows) == 2 and stats["type_correct"] == 0


def test_full_entity_annotation_penalizes_false_positives():
    sample = {"id": "test", "原始问题": "车轴怎么检查？", "问题类型": "工艺流程问题",
              "关键信息": {"部件": ["车轴"]}, "缺失信息": [], "处理标签": "RAG", "实体标注完整": True}
    rows, stats = evaluate.run_mode("rules", samples=[sample])
    assert not rows[0]["关键信息正确"]
    assert stats["entity_micro"]["fp"] == 1
