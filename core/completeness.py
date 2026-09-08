"""按查询目的判断信息是否足够构造检索，而非判断是否足够直接维修。"""
from __future__ import annotations

HINTS = {
    "部件": "请说明具体部件，例如车轴、制动盘或空气弹簧。",
    "故障或现象": "请描述异常表现，例如异响、裂纹、漏油或发热。",
    "指标": "请说明检测指标，例如轮径、剩磁量或划伤深度。",
    "数值": "请提供实际测量值。",
    "单位": "请补充测量单位，例如mm、kN或MPa。",
    "工艺或部件": "请说明要执行的工艺或检修的部件。",
}


def check(question_type: str, entities: dict, question: str = "") -> tuple[str, list[str], str]:
    if question_type == "非动车检修问题":
        return "非本领域问题", [], ""
    missing = []
    has = lambda key: bool(entities.get(key))
    if question_type == "标准限度问题":
        # 部件更换条件也是合法规程查询，不凭空补出“更换周期”实体。
        condition_query = any(word in question for word in ("什么时候", "何时", "多久"))
        if not has("指标") and not (condition_query and has("部件")):
            if not has("部件"):
                missing.append("部件")
            missing.append("指标")
    elif question_type == "故障诊断问题":
        if not has("部件"):
            missing.append("部件")
        if not has("故障或现象") and not ("故障" in question and "表现" in question):
            missing.append("故障或现象")
    elif question_type == "工艺流程问题":
        if not has("部件") and not has("工艺"):
            missing.append("工艺或部件")
        elif not has("部件") and has("故障或现象"):
            missing.append("部件")
    elif question_type in ("超限处置问题", "条件判断问题"):
        if not has("部件"):
            missing.append("部件")
        specific_fault = any(item["标准词"] != "超限" for item in entities.get("故障或现象", []))
        if not has("指标") and not specific_fault:
            missing.append("指标" if not has("部件") or has("故障或现象") else "故障或现象")
        if question_type == "条件判断问题" and has("数值") and not has("单位"):
            missing.append("单位")
    elif question_type == "部件信息问题" and not has("部件"):
        missing.append("部件")
    if not missing:
        return "完整", [], ""
    return "信息不足", missing, " ".join(HINTS[field] for field in missing)


def missing_fields(question_type: str, entities: dict) -> list[str]:
    return check(question_type, entities)[1]
