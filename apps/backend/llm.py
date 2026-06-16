"""
LLM 调用 + JSON 解析兜底。

替代旧版 agent/ 目录（Manager/Strategy/Provider/exceptions 共 190 行）。
本质就是一次 chat.completions.create，加 3 级 JSON 解析兜底。
"""
import json
import re
from typing import Optional

from openai import OpenAI

from config import LLM_API_KEY, LLM_BASE_URL, LL_MODEL


def _get_client() -> OpenAI:
    if not LLM_API_KEY:
        raise RuntimeError("LLM_API_KEY 未配置，请在 .env 填写。")
    return OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL, timeout=300.0)


# 模块级单例客户端，避免每次请求重建
_client: Optional[OpenAI] = None


def _client_singleton() -> OpenAI:
    global _client
    if _client is None:
        _client = _get_client()
    return _client


def call_llm(prompt: str, expect_json: bool = False):
    """
    调用 LLM。

    Args:
        prompt: 完整提示词。
        expect_json: True 则解析返回为 dict（3 级兜底）；False 则返回纯文本。

    Returns:
        dict（expect_json=True）或 str（expect_json=False）。
    """
    client = _client_singleton()
    response = client.chat.completions.create(
        model=LL_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        top_p=0.9,
        timeout=300,
    )
    text = response.choices[0].message.content or ""

    if expect_json:
        return parse_json_lenient(text)
    return text


# ── JSON 解析兜底（照搬旧版 JSONWrapper 的 3 级策略）──────────────────

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]+?)```", re.IGNORECASE)


def _find_balanced_json(text: str) -> str | None:
    """
    从第一个 { 开始，按字符串字面量/转义 跳过后配对找对应 }。
    避免正则贪婪把多个对象拼成一个（这是大模型返回里很常见的 bug）。
    """
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def parse_json_lenient(text: str) -> dict:
    """
    容错解析 LLM 返回的 JSON 文本。3 级兜底：
      1. 直接 json.loads
      2. 抽 ```json ... ``` 代码块再解析
      3. 平衡括号抽第一个 {...} 再解析（替代原先的贪婪正则）
    全部失败抛 ValueError。
    """
    if not text:
        raise ValueError("LLM 返回为空，无法解析 JSON")

    text = text.strip()

    # 1. 直接解析
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    # 2. 抽 ```json``` 代码块
    m = _JSON_FENCE_RE.search(text)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except (json.JSONDecodeError, TypeError):
            pass

    # 3. 平衡括号抽 {...}
    candidate = _find_balanced_json(text)
    if candidate:
        try:
            return json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            pass

    raise ValueError(f"LLM 返回无法解析为 JSON，前 200 字: {text[:200]}")
