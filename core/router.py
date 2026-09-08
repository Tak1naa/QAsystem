"""将理解结果分配到规程检索、知识图谱或澄清流程。"""
REASONS = {
    "标准限度问题": "需要检索规程中的限度、允许范围或更换条件。",
    "工艺流程问题": "需要检索规程中的操作步骤和检修要求。",
    "超限处置问题": "需要检索与该缺陷或超限指标相关的处置条款。",
    "条件判断问题": "需要结合具体测量条件检索适用的规程条款。",
    "概念解释问题": "需要检索规程中的术语定义和上下文。",
    "故障诊断问题": "可查询知识图谱中部件、现象与故障原因的关联。",
    "部件信息问题": "可查询知识图谱中部件组成、功能和连接关系。",
}


def route(question_type: str, completeness: str, missing: list[str]) -> dict[str, str]:
    if question_type == "非动车检修问题":
        return {"标签": "OUT_OF_SCOPE", "理由": "问题不属于动车检修范围，不进入检修知识查询。"}
    if missing or completeness == "信息不足":
        return {"标签": "CLARIFY", "理由": f"缺少{'、'.join(missing)}，先补充信息再确定检索条件。"}
    label = "KG" if question_type in ("故障诊断问题", "部件信息问题") else "RAG"
    return {"标签": label, "理由": REASONS[question_type]}
