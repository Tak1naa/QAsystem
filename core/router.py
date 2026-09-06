"""
处理建议路由器 —— 根据问题类型和信息完整性生成后续处理建议。

路由规则：
  OUT_OF_SCOPE  ← 非检修问题
  CLARIFY       ← 信息不完整
  KG            ← 故障诊断问题（查知识图谱中的现象-故障-原因关系）
  RAG           ← 标准限度/工艺流程/超限处置（查规程知识库原文）
"""
from __future__ import annotations
from typing import Any

# ============================================================
# 各类型 → 路由标签 + 理由
# ============================================================
_TYPE_ROUTE: dict[str, tuple[str, str]] = {
    "标准限度问题": (
        "RAG",
        "标准限度问题需要查找检修规程原文中的具体数值标准和公差范围，适合进入规程知识库（RAG）检索。",
    ),
    "故障诊断问题": (
        "KG",
        "故障诊断问题包含部件和故障现象信息，适合查询知识图谱（KG）中的现象-故障-原因关联关系。",
    ),
    "工艺流程问题": (
        "RAG",
        "工艺流程问题需要查找检修规程原文中的操作步骤和方法描述，适合进入规程知识库（RAG）检索。",
    ),
    "超限处置问题": (
        "RAG",
        "超限处置问题需要查找检修规程中针对参数超限的处理规定和操作指引，适合进入规程知识库（RAG）检索。",
    ),
    "非动车检修问题": (
        "OUT_OF_SCOPE",
        "该问题不属于动车检修规程问答范围，不进入后续检修知识查询流程。",
    ),
}


def route(question_type: str, completeness: str, missing: list[str]) -> dict[str, str]:
    """
    生成处理建议。

    Args:
        question_type: 问题类型
        completeness: 信息完整性级别
        missing: 缺失字段列表

    Returns:
        {"标签": "RAG|KG|CLARIFY|OUT_OF_SCOPE", "理由": "..."}
    """
    # 非检修
    if question_type == "非动车检修问题":
        label, reason = _TYPE_ROUTE["非动车检修问题"]
        return {"标签": label, "理由": reason}

    # 信息不完整
    if completeness == "信息不足":
        field_names = "、".join(missing)
        return {
            "标签": "CLARIFY",
            "理由": f"当前问题缺少{field_names}等关键信息，无法判断应查规程知识库还是知识图谱，建议先引导用户补充信息。",
        }

    # 正常路由
    label, reason = _TYPE_ROUTE.get(
        question_type,
        ("RAG", "问题信息完整，可进入后续知识查询模块。"),
    )
    return {"标签": label, "理由": reason}
