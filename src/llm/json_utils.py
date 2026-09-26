"""
Robust JSON extraction from LLM responses.

LLMs wrap JSON in prose, Markdown fences or <think> blocks, leave trailing
commas, and get cut off at the token limit. extract_json() handles all of
these and returns None only when no JSON object can be recovered.
"""
import json
import re
from typing import Optional

_THINK = re.compile(r"<think>.*?(</think>|$)", re.DOTALL)
_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_TRAILING_COMMA = re.compile(r",\s*([}\]])")


def _loads(text: str) -> Optional[dict]:
    for candidate in (text, _TRAILING_COMMA.sub(r"\1", text)):
        try:
            value = json.loads(candidate)
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            continue
    return None


def _close_truncated(text: str) -> str:
    """Close strings, arrays and objects left open by a cut-off response."""
    stack, in_string, escaped = [], False, False
    for ch in text:
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
        elif ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]" and stack:
            stack.pop()
    repaired = text + ('"' if in_string else "")
    # Drop a dangling key or comma before closing
    repaired = re.sub(r',\s*"[^"]*"\s*:?\s*$|,\s*$|:\s*$', "", repaired.rstrip())
    return repaired + "".join(reversed(stack))


def extract_json(response: str) -> Optional[dict]:
    """Return the first JSON object in an LLM response, or None."""
    if not response:
        return None
    text = _THINK.sub("", response).strip()

    fenced = _FENCE.search(text)
    if fenced and (value := _loads(fenced.group(1))) is not None:
        return value

    start = text.find("{")
    if start == -1:
        return None

    # Try each "{" from the left, so the outermost object wins over nested ones.
    # At each position accept a complete object, else repair a truncated one.
    decoder = json.JSONDecoder()
    for i in range(start, len(text)):
        if text[i] != "{":
            continue
        candidate = _TRAILING_COMMA.sub(r"\1", text[i:].replace("```", ""))
        try:
            value, _ = decoder.raw_decode(candidate)
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            repaired = _loads(_close_truncated(candidate))
            if repaired is not None:
                return repaired
    return None

def loads_llm_json(response: str) -> dict:
    """Drop-in for json.loads on LLM output: raises JSONDecodeError if nothing is recoverable."""
    value = extract_json(response)
    if value is None:
        raise json.JSONDecodeError("No JSON object found in LLM response", response or "", 0)
    return value
