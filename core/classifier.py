"""根据问句意图和领域实体识别问题类型。"""
from __future__ import annotations
import re

OUTSIDE = re.compile(r"天气|股票|火锅|餐厅|电影|旅游|手机|游戏|彩票|轮胎|跑多快")
CAUSE = re.compile(r"什么原因|为何|为什么|怎么回事|哪里.*问题|哪.*问题|导致|引起|故障.*表现")
LIMIT = re.compile(r"多少|多大|多厚|多深|多长|多久|什么时候|何时|标准|限度|限值|公差|范围|算正常")
DISPOSAL = re.compile(r"怎么办|怎么处理|如何处置|能修|能用|还能|可以.*修|要不要换|需不需要换")
OVER = re.compile(r"超限|超标|超了|超出|过大|太大|超过|不符合|不满足|数据不对")
PROCESS = re.compile(r"怎么|如何|怎样|步骤|流程|顺序|要求|注意|方法|哪些尺寸")
CONDITION = re.compile(r"(?:小于|大于|低于|高于|超过|[<>≤≥])\s*[+-]?\d")
CONCEPT = re.compile(r"什么是|是什么意思|含义|定义")
COMPONENT = re.compile(r"组成|包括哪些|哪些部件|什么作用|功能|用途")


def classify(question: str, entities: dict) -> tuple[str, float]:
    has_domain = any(entities.get(k) for k in ("部件", "故障或现象", "工艺", "指标"))
    if "轮胎" in question or "汽车" in question:
        return "非动车检修问题", 0.94
    if OUTSIDE.search(question) and not entities.get("部件"):
        return "非动车检修问题", 0.94
    if CONCEPT.search(question) and has_domain:
        return "概念解释问题", 0.90
    if COMPONENT.search(question) and entities.get("部件"):
        return "部件信息问题", 0.88
    if CAUSE.search(question) and has_domain:
        return "故障诊断问题", 0.90
    # “超过多少”是在问限度，不等于已经超限。
    if LIMIT.search(question) and (has_domain or re.search(r"测|数值|数据|正常", question)):
        return "标准限度问题", 0.90 if has_domain else 0.50
    if OVER.search(question) or (DISPOSAL.search(question) and has_domain):
        return "超限处置问题", 0.86 if has_domain else 0.50
    if CONDITION.search(question) and has_domain:
        return "条件判断问题", 0.85
    if PROCESS.search(question) and has_domain:
        return "工艺流程问题", 0.85
    if not has_domain:
        return "非动车检修问题", 0.70
    if entities.get("工艺"):
        return "工艺流程问题", 0.62
    if entities.get("故障或现象"):
        return "故障诊断问题", 0.60
    if entities.get("指标"):
        return "标准限度问题", 0.55
    return "故障诊断问题", 0.45
