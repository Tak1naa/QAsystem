"""Streamlit演示入口，共用main.analyze，页面不重复实现业务规则。"""
import html
import json
import re
import time
from pathlib import Path

import streamlit as st

from config import DEEPSEEK_API_KEY
from main import analyze

st.set_page_config(page_title="动车检修 · 问题理解", page_icon="🚆", layout="wide")
st.markdown("""
<style>
.block-container {max-width:1180px;padding-top:2.4rem}
h1 {letter-spacing:-0.04em}
.entity {line-height:2.4;padding:3px 5px!important;border-radius:4px!important}
.entity small {font-size:10px;opacity:.65;margin-left:3px}
.question-banner {padding:20px 24px;border:1px solid #cbd5e1;border-radius:12px;font-size:19px}
</style>
""", unsafe_allow_html=True)

HIGHLIGHT_COLORS = {
    "部件": "#dbeafe", "故障或现象": "#fee2e2", "工艺": "#d1fae5",
    "指标": "#fef3c7", "数值": "#ede9fe", "单位": "#e0e7ff",
}

def highlight(question: str, entities: dict) -> str:
    matches: list[tuple[int, int, str, str]] = []
    for category, values in entities.items():
        for item in values:
            term = item["原始词"]
            for m in re.finditer(re.escape(term), question, re.I):
                matches.append((m.start(), m.end(), category, term))
    if not matches:
        return html.escape(question)
    matches.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    filtered: list[tuple[int, int, str, str]] = []
    occupied_end = 0
    for start, end, cat, term in matches:
        if start >= occupied_end:
            filtered.append((start, end, cat, term))
            occupied_end = end
    escaped = []
    cursor = 0
    # 下标来自原文，必须逐段转义，不能先转义全文再使用旧下标。
    for start, end, category, term in filtered:
        escaped.append(html.escape(question[cursor:start]))
        color = HIGHLIGHT_COLORS.get(category, "rgba(128,128,128,0.10)")
        tag = (
            f"<mark class='entity' style='background:{color};border-radius:2px;padding:1px 4px'>"
            f"{html.escape(question[start:end])}"
            f"<small> {category}</small></mark>"
        )
        escaped.append(tag)
        cursor = end
    escaped.append(html.escape(question[cursor:]))
    return "".join(escaped)


def use_example(question: str) -> None:
    st.session_state["question"] = question


with st.sidebar:
    st.header("演示设置")
    mode = st.selectbox("处理模式", ["rules", "hybrid", "llm"],
                        format_func=lambda x: {"rules": "纯规则", "hybrid": "混合模式", "llm": "大模型优先"}[x])
    st.caption("混合模式在规则置信度不足时调用大模型。调用失败会保留规则结果。")
    st.caption("在线接口：已配置" if DEEPSEEK_API_KEY else "在线接口：未配置，使用离线规则即可演示")
    st.divider()
    st.subheader("示例问题")
    for question in [
        "轴箱有点响，可能是哪的问题？",
        "车轴划伤深度超过1mm怎么处理？",
        "这个超了怎么办？",
        "车轮直径小于800mm是否报废？",
        "轮对包括哪些部件？",
        "什么是磁粉探伤？",
        "今天北京天气怎么样？",
    ]:
        st.button(question, on_click=use_example, args=(question,), use_container_width=True)

st.caption("铁路信息技术专业实践 / 项目三")
st.title("动车检修问题理解与处理建议")
st.write("识别问题意图与检修信息，补全查询条件，再选择规程知识库或知识图谱。")

question = st.text_input("输入检修问题", key="question", placeholder="例如：车轴划伤深度超过1mm怎么处理？")
submitted = st.button("分析问题", type="primary")
if submitted:
    started = time.perf_counter()
    try:
        with st.spinner("正在分析…"):
            result = analyze(question, mode)
        st.session_state["result"] = result
        st.session_state["response_ms"] = (time.perf_counter() - started) * 1000
    except ValueError as exc:
        st.session_state.pop("result", None)
        st.warning(str(exc))

result = st.session_state.get("result")
if result:
    st.divider()
    st.markdown(f'<div class="question-banner">{highlight(result["原始问题"], result["已识别信息"])}</div>', unsafe_allow_html=True)
    st.caption("颜色分别标出部件、故障现象、工艺、指标、数值和单位。结果对应上方高亮的问题。")
    columns = st.columns(4)
    columns[0].metric("问题类型", result["问题类型"].removesuffix("问题"))
    columns[1].metric("信息完整性", result["信息完整性"])
    columns[2].metric("建议方向", result["处理建议"]["标签"])
    columns[3].metric("分类置信度", f'{result["置信度"]:.0%}')
    st.caption("置信度反映规则匹配强度或模型自评，不是经概率校准的正确率。")

    left, right = st.columns([3, 2])
    with left:
        st.subheader("识别与标准化")
        entities = []
        for category, values in result["标准化信息"].items():
            for item in values:
                entities.append({"类别": category, "原始表述": item["原始词"], "标准术语": item["标准词"]})
        if entities:
            st.dataframe(entities, hide_index=True, use_container_width=True)
        else:
            st.info("没有识别到明确的检修实体。")
    with right:
        st.subheader("下一步处理")
        st.write(result["处理建议"]["理由"])
        if result["缺失信息"]:
            st.warning("需要补充：" + "、".join(result["缺失信息"]))
            st.info(result["澄清提示"])
        elif result["处理建议"]["标签"] != "OUT_OF_SCOPE":
            st.success("信息可用于构造后续查询。")
        if result["元数据"].get("fallback_used"):
            st.warning("在线调用未成功，本次结果来自规则回退。")
            st.caption(result["元数据"].get("fallback_reason", ""))

    st.subheader("运行记录")
    timing = result["运行耗时"]
    cols = st.columns(4)
    for col, label, value in zip(cols, ["规则处理", "在线尝试", "后端总耗时", "页面调用往返"],
                                 [timing["规则耗时_ms"], timing["大模型耗时_ms"], timing["总耗时_ms"], st.session_state["response_ms"]]):
        col.metric(label, f"{value:.2f} ms")
    st.caption(f'请求模式：{result["处理模式"]} · 实际来源：{result["元数据"]["source"]}。页面调用往返包括页面端同步调用和提示开销，不包含浏览器绘制。')
    with st.expander("查看JSON与分阶段耗时"):
        st.json(result)
    st.download_button("下载本次分析JSON", json.dumps(result, ensure_ascii=False, indent=2),
                       file_name="analysis.json", mime="application/json")

    with st.expander("查看命中术语的PDF来源"):
        source_path = Path(__file__).parent / "data/terminology_sources.json"
        source = json.loads(source_path.read_text(encoding="utf-8"))
        found = {(category, item["标准词"]) for category, values in result["标准化信息"].items() for item in values}
        records = [r for r in source["术语"] if (r["类别"], r["标准术语"]) in found]
        for record in records:
            page = record.get("PDF页码")
            st.markdown(f'**{record["标准术语"]}** · ' + (f'PDF第{page}页 / 印刷页{record["印刷页码"]} · {record["章节"]}' if page else '问句理解扩展词'))
            st.write(record.get("原文摘录") or record.get("扩展理由", ""))
else:
    st.info("输入一个问题，或从左侧选择示例，再点击“分析问题”。")
    cols = st.columns(3)
    for col, title, detail in zip(cols, ["理解意图", "补齐信息", "建议知识源"],
                                  ["支持标准、故障、工艺等8类问题。", "明确列出缺失字段并给出补充提示。", "输出RAG、KG、CLARIFY或OUT_OF_SCOPE。"]):
        col.subheader(title)
        col.write(detail)

st.divider()
st.caption("本项目输出问题理解和检索建议；具体维修结论仍需查询适用规程。")

