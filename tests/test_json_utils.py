"""
Tests for robust LLM JSON extraction
"""
import json

import pytest

from src.llm.json_utils import extract_json, loads_llm_json


def test_plain_json():
    assert extract_json('{"score": 80}') == {"score": 80}


def test_fenced_json_with_prose():
    text = 'Here is the result:\n```json\n{"score": 80, "note": "ok"}\n```\nHope this helps.'
    assert extract_json(text) == {"score": 80, "note": "ok"}


def test_think_block_with_braces_is_ignored():
    text = '<think>Maybe {price} matters more than {risk}...</think>\n{"score": 72}'
    assert extract_json(text) == {"score": 72}


def test_unclosed_think_block():
    assert extract_json('<think>still reasoning about {x}') is None


def test_trailing_commas():
    assert extract_json('{"a": [1, 2,], "b": 3,}') == {"a": [1, 2], "b": 3}


def test_truncated_response_is_repaired():
    text = '```json\n{"breakdown": {"price": {"score": 75, "reasoning": "Competitive pric'
    result = extract_json(text)
    assert result["breakdown"]["price"]["score"] == 75


def test_truncated_after_key():
    result = extract_json('{"overall_score": 83, "recommendation": "APPROVED", "key_findings": ["a", "b"], "reas')
    assert result == {"overall_score": 83, "recommendation": "APPROVED", "key_findings": ["a", "b"]}


def test_no_json():
    assert extract_json("I cannot help with that.") is None
    with pytest.raises(json.JSONDecodeError):
        loads_llm_json("I cannot help with that.")


def test_grader_flags_unparseable_response():
    from src.processors.vendor_grader import VendorGrader

    result = VendorGrader()._parse_grading_response("Sorry, no JSON here.", ["price", "risk"])
    assert result["parse_failed"] is True
    assert set(result["breakdown"]) == {"price", "risk"}


def test_grader_recovers_truncated_response():
    from src.processors.vendor_grader import VendorGrader

    truncated = '```json\n{"breakdown": {"price": {"score": 75, "reasoning": "Fair"}, "quality": {"score": 9'
    result = VendorGrader()._parse_grading_response(truncated, ["price", "quality"])
    assert "parse_failed" not in result
    assert result["breakdown"]["price"]["score"] == 75
