from __future__ import annotations

import html
import re

import streamlit as st

from main import analyze

st.set_page_config(page_title="动车检修问题理解系统", page_icon="", layout="wide")

# ═══════════════════════════════════════════════════════════
#  Typography & layout
#  字体栈：JetBrains Mono → SF Mono → Menlo → monospace
#  布局：非对称双栏，留白区隔，无卡片边框
# ═══════════════════════════════════════════════════════════
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');

    /* ── animation keyframes ── */
    @keyframes fadeSlideIn {
        from { opacity: 0; transform: translateY(12px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    @keyframes popIn {
        0%   { transform: scale(0.94); opacity: 0; }
        60%  { transform: scale(1.06); }
        100% { transform: scale(1);    opacity: 1; }
    }
    @keyframes pulseGlow {
        0%, 100% { box-shadow: 0 0 0 0 rgba(13,148,136,0); }
        50%      { box-shadow: 0 0 0 6px rgba(13,148,136,0.12); }
    }
    @keyframes drawBorder {
        from { border-left-color: transparent; }
        to   { border-left-color: rgba(128,128,128,0.35); }
    }
    @keyframes countUp {
        from { opacity: 0.3; transform: scale(0.9); }
        to   { opacity: 1;    transform: scale(1); }
    }
    @keyframes slideInRight {
        from { opacity: 0; transform: translateX(20px); }
        to   { opacity: 1; transform: translateX(0); }
    }

    /* ── applied animations ── */
    .banner {
        animation: fadeSlideIn 0.4s cubic-bezier(0.34,1.56,0.64,1) both,
                   drawBorder 0.6s ease-out both;
        animation-delay: 0s, 0.1s;
    }
    .card, .panel, [class*="stColumns"] > div:first-child > * {
        animation: fadeSlideIn 0.5s cubic-bezier(0.34,1.56,0.64,1) both;
        animation-delay: 0.15s;
    }
    [class*="stColumns"] > div:last-child > * {
        animation: slideInRight 0.5s cubic-bezier(0.34,1.56,0.64,1) both;
        animation-delay: 0.25s;
    }
    .big-val {
        animation: popIn 0.5s cubic-bezier(0.34,1.56,0.64,1) both;
        animation-delay: 0.35s;
    }
    .rte {
        animation: popIn 0.4s cubic-bezier(0.34,1.56,0.64,1) both;
        animation-delay: 0.2s;
    }
    .tag {
        transition: transform 0.18s cubic-bezier(0.34,1.56,0.64,1);
    }
    .tag:hover {
        transform: scale(1.12);
    }
    .stButton button {
        transition: transform 0.15s cubic-bezier(0.34,1.56,0.64,1),
                    box-shadow 0.15s ease;
    }
    .stButton button:hover {
        transform: scale(1.04);
    }
    .stButton button:active {
        transform: scale(0.96);
    }

    /* ── dot-grid background ── */
    .stApp {
        --dot-color: rgba(128,128,128,0.12);
        background-image:
            radial-gradient(circle, var(--dot-color) 1.2px, transparent 1.2px);
        background-size: 14px 14px;
    }
    .main > div {
        background: transparent !important;
    }

    * { font-family: 'JetBrains Mono', 'SF Mono', 'Menlo', 'Consolas', monospace; }

    .stMarkdown, .stMarkdown *,
    [data-testid="stNotification"],
    [data-testid="stNotification"] *,
    [data-testid="stCaptionContainer"],
    .stButton button,
    .stTextInput input,
    .stTextInput textarea,
    .stWarning, .stInfo, .stSuccess, .stError,
    h1, h2, h3, h4, h5, h6, p, label, caption, figcaption,
    .stException, [data-testid="stException"] {
        font-family: 'JetBrains Mono', 'SF Mono', 'Menlo', 'Consolas', monospace !important;
    }

    [class*="material-symbols"], [class*="material-icons"],
    [data-testid="stExpanderToggle"],
    button[data-testid="stSidebarCollapseButton"],
    button[data-testid="baseButton-headerNoPadding"] {
        font-family: 'Material Symbols Outlined', 'Material Icons', sans-serif !important;
    }

    .banner {
        background: transparent;
        border: 1px solid rgba(128,128,128,0.18);
        border-left: 2px solid rgba(128,128,128,0.35);
        padding: 16px 24px; font-size: 16px; line-height: 2.2;
        margin-bottom: 28px;
    }
    .banner mark.entity { border-radius: 2px; padding: 1px 5px; }
    .banner mark.entity small { font-size: 0.5em; opacity: 0.55; margin-left: 1px; font-weight: 600; text-transform: uppercase; }

    .panel {
        background: transparent;
        border: 1px solid rgba(128,128,128,0.12);
        padding: 20px 24px; margin-bottom: 14px;
    }

    .label {
        font-size: 9px; font-weight: 600; letter-spacing: 1.5px;
        text-transform: uppercase; opacity: 0.35; margin-bottom: 10px;
    }

    .big-val {
        font-size: 48px; font-weight: 700; letter-spacing: -1.5px; line-height: 1;
    }

    .divider { border: 0; border-top: 1px solid rgba(128,128,128,0.12); margin: 22px 0; }

    .rte {
        display: inline-block; font-size: 15px; font-weight: 700;
        padding: 4px 18px; border-radius: 2px;
    }
    .rte-RAG           { background: rgba(13,148,136,0.12);  color: #0d9488; }
    .rte-KG            { background: rgba(5,150,105,0.12);   color: #059669; }
    .rte-CLARIFY       { background: rgba(217,119,6,0.12);   color: #d97706; }
    .rte-OUT_OF_SCOPE  { background: rgba(128,128,128,0.10); color: #888; }

    .cpl {
        display: inline-block; font-size: 11px; font-weight: 600;
        padding: 2px 8px; border-radius: 2px; letter-spacing: 0.3px;
    }
    .cpl-完整      { background: rgba(5,150,105,0.12);  color: #059669; }
    .cpl-基本完整  { background: rgba(217,119,6,0.12);  color: #d97706; }
    .cpl-不完整    { background: rgba(220,38,38,0.10);  color: #dc2626; }
    .cpl-不适用    { background: rgba(128,128,128,0.10); color: #888; }

    .tag {
        display: inline-block; font-size: 11px; margin: 0 3px 3px 0;
        padding: 1px 7px; border-radius: 2px;
    }
    .tag-部件       { background: rgba(59,130,246,0.15);  color: #2563eb; }
    .tag-故障或现象 { background: rgba(220,38,38,0.10);   color: #dc2626; }
    .tag-工艺       { background: rgba(5,150,105,0.12);   color: #059669; }
    .tag-指标       { background: rgba(217,119,6,0.12);   color: #d97706; }
    .tag-数值       { background: rgba(124,58,237,0.12);  color: #7c3aed; }
    .tag-单位       { background: rgba(124,58,237,0.12);  color: #7c3aed; }

    .et { width: 100%; border-collapse: collapse; font-size: 13px; }
    .et td { padding: 5px 8px; border-bottom: 1px solid rgba(128,128,128,0.10); }
    .et td:first-child { opacity: 0.4; font-weight: 600; width: 80px; padding-left: 0; font-size: 9px; letter-spacing: 1px; text-transform: uppercase; }
    .et tr:last-child td { border-bottom: 0; }

    .timing { font-size: 11px; opacity: 0.4; font-family: 'JetBrains Mono', monospace; }
    .timing span { margin-right: 14px; }
</style>
""", unsafe_allow_html=True)

HIGHLIGHT_COLORS = {
    "部件": "rgba(59,130,246,0.15)", "故障或现象": "rgba(220,38,38,0.10)",
    "工艺": "rgba(5,150,105,0.12)", "指标": "rgba(217,119,6,0.12)",
    "数值": "rgba(124,58,237,0.12)", "单位": "rgba(124,58,237,0.12)",
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
    escaped = list(html.escape(question))
    for start, end, category, term in sorted(filtered, key=lambda x: -x[0]):
        color = HIGHLIGHT_COLORS.get(category, "rgba(128,128,128,0.10)")
        tag = (
            f"<mark class='entity' style='background:{color};border-radius:2px;padding:1px 4px'>"
            f"{html.escape(term)}"
            f"<small> {category}</small></mark>"
        )
        escaped[start:end] = [tag]
    return "".join(escaped)


def _entity_table(entities: dict, key_name: str = "原始词") -> str:
    tag_class = {
        "部件": "tag-部件", "故障或现象": "tag-故障或现象",
        "工艺": "tag-工艺", "指标": "tag-指标",
        "数值": "tag-数值", "单位": "tag-单位",
    }
    rows = []
    for field, values in entities.items():
        if values:
            tags_html = " ".join(
                f"<span class='tag {tag_class.get(field, '')}'>{html.escape(v[key_name])}</span>"
                for v in values
            )
            rows.append(f"<tr><td>{field}</td><td>{tags_html}</td></tr>")
    if not rows:
        return "<p style='font-size:12px;opacity:0.35'>--</p>"
    return f"<table class='et'>{''.join(rows)}</table>"


# Sidebar
with st.sidebar:
    st.markdown("**Mode**")
    mode = st.selectbox(
        "mode", ["hybrid", "rules", "llm"],
        label_visibility="collapsed",
        format_func=lambda x: {"hybrid": "Hybrid", "rules": "Rules", "llm": "LLM"}[x],
    )
    st.markdown("**Samples**")
    examples = [
        "轴箱有点响，应该怎么办？",
        "车轮直径小于多少需要更换？",
        "车轴划伤深度超过1mm怎么处理？",
        "这个超了怎么办？",
        "今天北京天气怎么样？",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True):
            st.session_state["question"] = ex

# Header
st.markdown(
    "<h1 class='app-title' style='font-size:38px;font-weight:700;letter-spacing:-1.2px;margin-bottom:8px;line-height:1.2'>"
    "动车检修问题理解与处理建议系统</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p class='app-subtitle' style='font-size:11px;opacity:0.35;margin-top:0;margin-bottom:3px;text-transform:uppercase;letter-spacing:1.5px'>"
    "EMU Maintenance Q&amp;A &middot; Hexie 2C Level-4 repair procedures"
    "</p>",
    unsafe_allow_html=True,
)
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# Input
default_question = st.session_state.get("question", "")
col_input, col_btn = st.columns([5, 1])
with col_input:
    question = st.text_input(
        "Question",
        value=default_question,
        placeholder="ask anything about EMU maintenance...",
        label_visibility="collapsed",
    )
with col_btn:
    analyze_clicked = st.button("Run", type="primary", use_container_width=True)

# Empty
if not analyze_clicked:
    st.markdown(
        "<p style='opacity:0.35;margin-top:60px;font-size:13px;max-width:480px'>"
        "Enter a natural language maintenance question. The system identifies intent, "
        "extracts entities (component, fault, process, metric, value), checks completeness, "
        "and routes to the appropriate backend (document retrieval, knowledge graph, or clarification)."
        "</p>",
        unsafe_allow_html=True,
    )

# Results
if analyze_clicked:
    question_text = (question or "").strip()
    if not question_text:
        st.warning("Please enter a question.")
    else:
        try:
            result = analyze(question_text, mode)

            highlighted = highlight(question_text, result["已识别信息"])
            st.markdown(f"<div class='banner'>{highlighted}</div>", unsafe_allow_html=True)

            left, right = st.columns([5, 3])

            with left:
                st.markdown("<div class='label'>Recognition</div>", unsafe_allow_html=True)
                st.markdown(_entity_table(result["已识别信息"]), unsafe_allow_html=True)
                st.markdown("<div class='label' style='margin-top:24px'>Normalized</div>", unsafe_allow_html=True)
                st.markdown(_entity_table(result["标准化信息"], key_name="标准词"), unsafe_allow_html=True)

            with right:
                st.markdown("<div class='label'>Route</div>", unsafe_allow_html=True)
                route = result["处理建议"]
                label = route["标签"]
                rc = f"rte-{label}" if label else ""
                st.markdown(
                    f"<span class='rte {rc}'>{html.escape(label) or '--'}</span>",
                    unsafe_allow_html=True,
                )

                st.markdown("<div class='label' style='margin-top:24px'>Confidence</div>", unsafe_allow_html=True)
                confidence = result["置信度"]
                st.markdown(f"<div class='big-val'>{confidence:.0%}</div>", unsafe_allow_html=True)
                st.progress(confidence)

                st.markdown("<div class='label' style='margin-top:24px'>Completeness</div>", unsafe_allow_html=True)
                completeness = result["信息完整性"]
                cc = f"cpl-{completeness}" if completeness else ""
                st.markdown(f"<span class='cpl {cc}'>{html.escape(completeness) or '--'}</span>", unsafe_allow_html=True)

                st.markdown("<div class='label' style='margin-top:24px'>Type</div>", unsafe_allow_html=True)
                st.markdown(f"<span style='font-size:14px'>{html.escape(result['问题类型'])}</span>", unsafe_allow_html=True)

                t = result["运行耗时"]
                st.markdown("<div class='label' style='margin-top:24px'>Latency</div>", unsafe_allow_html=True)
                st.markdown(
                    f"<div class='timing'>"
                    f"<span>rules {t['规则耗时_ms']}ms</span>"
                    f"<span>llm {t['大模型耗时_ms']}ms</span>"
                    f"<span>total {t['总耗时_ms']}ms</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            st.markdown(
                f"<p style='margin-top:20px;font-size:13px;opacity:0.55;max-width:680px'>"
                f"{html.escape(route.get('理由', ''))}</p>",
                unsafe_allow_html=True,
            )

            missing = result["缺失信息"]
            clarify = result["澄清提示"]
            if missing:
                st.warning(f"Missing: {'、'.join(missing)}")
            if clarify:
                st.info(clarify)
            if result["元数据"].get("fallback_used"):
                st.warning("LLM unavailable; fell back to rules mode.")

            with st.expander("Raw output"):
                st.json(result)

        except ValueError as exc:
            st.warning(str(exc))

