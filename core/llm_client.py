from __future__ import annotations

import json
import re
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from config import LLM_TIMEOUT_SECONDS, OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
from core.schemas import validate_result

SYSTEM_PROMPT = """你是动车组检修问题理解模块。只输出一个 JSON 对象，不要 Markdown。
问题类型只能是：标准限度问题、故障诊断问题、工艺流程问题、超限处置问题、非动车检修问题。
处理建议标签只能是：RAG、KG、CLARIFY、OUT_OF_SCOPE。
JSON 必须包含：问题类型、已识别信息、标准化信息、缺失信息、信息完整性、澄清提示、处理建议、置信度。
已识别信息和标准化信息均须包含：部件、故障或现象、工艺、指标、数值、单位；每项是 {原始词, 标准词} 对象数组。
不要编造规程数值；信息不足时使用 CLARIFY。"""


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    return json.loads(cleaned)


def analyze_with_llm(question: str) -> tuple[dict[str, Any], float]:
    """Call an OpenAI-compatible endpoint and retry once on invalid output."""
    if not OPENAI_API_KEY:
        raise RuntimeError("未配置 OPENAI_API_KEY")
    started = time.perf_counter()
    endpoint = f"{OPENAI_BASE_URL}/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            payload = {
                "model": OPENAI_MODEL,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": question + ("\n请修正为严格 JSON。" if attempt else "")},
                ],
            }
            request = Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urlopen(request, timeout=LLM_TIMEOUT_SECONDS) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
            text = response_payload["choices"][0]["message"]["content"]
            result = validate_result(_extract_json(text), question, "llm")
            elapsed = round((time.perf_counter() - started) * 1000, 2)
            result["运行耗时"] = {"规则耗时_ms": 0.0, "大模型耗时_ms": elapsed, "总耗时_ms": elapsed}
            result["元数据"] = {"fallback_used": False, "low_confidence": result["置信度"] < 0.65, "source": "llm"}
            return result, elapsed
        except (HTTPError, URLError, OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
            last_error = exc
    raise RuntimeError(f"LLM 调用或结果校验失败：{last_error}")
