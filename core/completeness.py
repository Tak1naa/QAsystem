"""
信息完整性检查器 —— 判断问题提供的信息是否足够做出有效回答，
并在信息不足时生成澄清提示。
"""
from __future__ import annotations
from typing import Any

# ============================================================
# 各类问题类型的必填字段
# ============================================================
REQUIREMENTS: dict[str, list[str]] = {
    "标准限度问题": ["指标"],
    "故障诊断问题": ["部件", "故障或现象"],
    "工艺流程问题": ["工艺或部件"],
    "超限处置问题": ["具体部件", "超限指标"],
    "非动车检修问题": [],
}

# 必填字段 → entities 字典中的检查键（entities 是 {字段: [{...}]} 格式）
_FIELD_TO_CHECK: dict[str, str] = {
    "指标": "指标",
    "部件": "部件",
    "故障或现象": "故障或现象",
    "工艺或部件": "工艺或部件",  # 由 check 函数特殊处理
    "具体部件": "部件",
    "超限指标": "指标",
}

# ============================================================
# 澄清提示模板 —— 缺什么、怎么补
# ============================================================
CLARIFY_TEMPLATES: dict[str, str] = {
    "指标": "请补充具体检测指标，例如：剩磁量、轮径、划伤深度、过盈量、扭矩、绝缘电阻等。",
    "部件": "请补充具体部件名称，例如：轮对轴箱、轴箱弹簧、车轮、车轴、构架等。",
    "故障或现象": "请描述具体的故障现象或异常表现，例如：异响、裂纹、磨损、腐蚀、发热等。",
    "工艺或部件": "请说明涉及的检修工艺（如探伤、打磨、压装）或具体部件名称。",
    "具体部件": "请补充具体的部件名称，例如：轮对轴箱、轴箱弹簧、车轮、车轴等。",
    "超限指标": "请补充超限的具体指标，例如：剩磁量、轮径、划伤深度、过盈量等。",
}


def check(question_type: str, entities: dict[str, list[dict[str, str]]]) -> tuple[str, list[str], str]:
    """
    检查问题信息完整性。

    Args:
        question_type: 问题类型
        entities: 标准化实体字典 {字段: [{原始词, 标准词}]}

    Returns:
        (完整性级别, 缺失字段列表, 澄清提示文本)
        完整性级别: "完整" / "信息不足" / "非本领域问题"
    """
    # 非检修问题
    if question_type == "非动车检修问题":
        return "非本领域问题", [], ""

    required = REQUIREMENTS.get(question_type, [])
    if not required:
        return "完整", [], ""

    # 检查每个必填字段
    missing: list[str] = []
    for req_field in required:
        check_key = _FIELD_TO_CHECK.get(req_field, req_field)
        if check_key == "工艺或部件":
            if not entities.get("工艺") and not entities.get("部件"):
                missing.append(req_field)
        else:
            if not entities.get(check_key):
                missing.append(req_field)

    if not missing:
        return "完整", [], ""

    # 生成澄清提示
    hints = []
    for field in missing:
        template = CLARIFY_TEMPLATES.get(field, f"请补充{field}信息。")
        hints.append(template)

    prompt = f"以上问题信息不全，请补充{'、'.join(missing)}。" + " ".join(hints)
    return "信息不足", missing, prompt


def missing_fields(question_type: str, entities: dict[str, list[dict[str, str]]]) -> list[str]:
    """便捷函数：仅返回缺失字段列表。"""
    _, missing, _ = check(question_type, entities)
    return missing
