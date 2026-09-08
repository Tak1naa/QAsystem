"""词典最长匹配与数值提取；只提取原文明确出现的信息。"""
from __future__ import annotations
import re

FIELDS = ("部件", "故障或现象", "工艺", "指标", "数值", "单位")
SEMANTIC_FIELDS = FIELDS[:4]
NUMBER = re.compile(r"(?<![\w.])[-+−]?\d+(?:\.\d+)?|(?<=[\u4e00-\u9fff<>=≤≥～~±])[-+−]?\d+(?:\.\d+)?")


def extract(question: str, terms: dict) -> tuple[dict, dict]:
    raw = {field: [] for field in FIELDS}
    normalized = {field: [] for field in FIELDS}
    excluded = [match.span() for match in re.finditer(r"(?:汽车|自行车)轮胎", question)]

    def add(field: str, original: str, standard: str) -> None:
        item = {"原始词": original, "标准词": standard}
        if item not in normalized[field]:
            raw[field].append(item.copy())
            normalized[field].append(item)

    for category in SEMANTIC_FIELDS:
        occupied = []
        pairs = {(alias, standard) for standard, aliases in terms.get(category, {}).items()
                 for alias in [standard, *aliases] if alias}
        for alias, standard in sorted(pairs, key=lambda p: (-len(p[0]), p[0])):
            # MT/UT等英文简称必须独立出现，避免命中型号中的片段。
            pattern = re.escape(alias)
            if alias.isascii() and alias.isalnum():
                pattern = r"(?<![A-Za-z0-9])" + pattern + r"(?![A-Za-z0-9])"
            for match in re.finditer(pattern, question, re.I):
                if any(match.start() < end and match.end() > start for start, end in excluded):
                    continue
                if alias == "MT" and match.group() != "MT":
                    continue
                if any(match.start() < end and match.end() > start for start, end in occupied):
                    continue
                occupied.append(match.span())
                add(category, match.group(), standard)

    unit_pairs = sorted(
        {(alias, standard) for standard, aliases in terms["单位"].items() for alias in [standard, *aliases]},
        key=lambda p: (-len(p[0]), p[0]),
    )
    unit_spans = []
    for alias, standard in unit_pairs:
        pattern = re.escape(alias)
        if alias.isascii():
            pattern = r"(?<![A-Za-z])" + pattern + r"(?![A-Za-z])"
        for match in re.finditer(pattern, question, re.I):
            if any(match.start() < end and match.end() > start for start, end in unit_spans):
                continue
            # 磁粉探伤的缩写MT不是毫特单位；无数值的MT只作工艺实体。
            if alias.lower() == "mt" and match.group() == "MT" and not re.search(r"\d\s*$", question[:match.start()]):
                continue
            unit_spans.append(match.span())
            add("单位", match.group(), standard)

    for match in NUMBER.finditer(question):
        before, after = question[:match.start()], question[match.end():]
        # 型号、螺栓规格、章节号和序号不作为测量值。
        if re.search(r"[A-Za-z]\s*$", before) or re.match(r"\d|\.\d", after):
            continue
        if after.startswith(("号", "次", "条")):
            continue
        add("数值", match.group(), match.group().replace("−", "-"))
    return raw, normalized
