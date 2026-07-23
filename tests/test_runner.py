import json

from votecastbench.runner import extract_json_object


def test_extract_json_object_accepts_plain_json() -> None:
    assert extract_json_object('{"a": 1}') == {"a": 1}


def test_extract_json_object_accepts_fenced_json() -> None:
    assert extract_json_object('```json\n{"a": 1}\n```') == {"a": 1}


def test_extract_json_object_recovers_surrounding_text() -> None:
    assert extract_json_object('Result:\n{"a": 1}\nDone.') == {"a": 1}


def test_extract_json_object_rejects_non_object() -> None:
    try:
        extract_json_object(json.dumps([1, 2]))
    except ValueError as exc:
        assert "not an object" in str(exc)
    else:
        raise AssertionError("expected ValueError")
