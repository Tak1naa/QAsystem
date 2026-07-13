from __future__ import annotations

import html
import re

import streamlit as st

from main import analyze

st.set_page_config(page_title="动车检修问题理解系统", page_icon="🚄", layout="wide")
st.title("🚄 动车检修问题理解与处理建议系统")
st.caption("规则模式可离线运行；LLM 或混合模式在 API 不可用时会自动回退到规则模式。")


def highlight(question: str, entities: dict) -> str:
    found = []
    colors = {"部件": "#dbeafe", "故障或现象": "#fee2e2", "工艺": "#dcfce7", "指标": "#fef3c7", "数值": "#f3e8ff", "单位": "#f3e8ff"}
    for category, values in entities.items():
        for item in values:
            found.append((item["原始词"], category))
    output = html.escape(question)
    for term, category in sorted(found, key=lambda x: len(x[0]), reverse=True):
        output = re.sub(re.escape(html.escape(term)), f"<mark style='background:{colors.get(category, '#e5e7eb')};border-radius:4px;padding:2px 4px'>{html.escape(term)}<small> {category}</small></mark>", output, count=1, flags=re.I)
    return output


with st.sidebar:
    mode = st.selectbox("处理模式", ["hybrid", "rules", "llm"], format_func={"hybrid": "混合模式（推荐）", "rules": "纯规则模式", "llm": "大模型模式"}.get)
    examples = ["轴箱有点响，应该怎么办？", "车轮直径小于多少需要更换？", "这个超了怎么办？", "今天北京天气怎么样？"]
    selected = st.selectbox("加载示例", [""] + examples)

question = st.text_area("请输入检修问题", value=selected, placeholder="例如：车轴划伤深度超过1mm怎么处理？", height=110)
if st.button("开始分析", type="primary"):
    try:
        result = analyze(question, mode)
        left, right = st.columns([2, 1])
        with left:
            st.subheader("识别结果")
            st.markdown(highlight(question, result["已识别信息"]), unsafe_allow_html=True)
            st.write("问题类型：", result["问题类型"])
            st.write("信息完整性：", result["信息完整性"])
            st.write("缺失信息：", "、".join(result["缺失信息"]) or "无")
            if result["澄清提示"]:
                st.info(result["澄清提示"])
            st.json(result["标准化信息"], expanded=False)
        with right:
            route = result["处理建议"]
            st.subheader("处理建议")
            st.metric("路由标签", route["标签"])
            st.write(route["理由"])
            st.metric("置信度", f"{result['置信度']:.0%}")
            timing = result["运行耗时"]
            st.caption(f"规则 {timing['规则耗时_ms']} ms · LLM {timing['大模型耗时_ms']} ms · 总计 {timing['总耗时_ms']} ms")
            if result["元数据"].get("fallback_used"):
                st.warning("大模型不可用，已自动回退至纯规则模式。")
        st.subheader("统一 JSON 输出")
        st.json(result)
    except ValueError as exc:
        st.warning(str(exc))

