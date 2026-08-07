import json

import pytest

from shadowforge.evidence import EvidenceError, EvidenceStore


def append_record(store, execution_id="1"):
    return store.append(
        execution_id=execution_id,
        scope="lab",
        tool="fake",
        target="192.0.2.1",
        arguments={"x": 1},
        status="ok",
        duration_ms=10,
        shadowforge_version="0.1.0",
        result={"value": 1},
    )


def test_evidence_records_are_hash_chained(tmp_path):
    store = EvidenceStore(tmp_path / "evidence.jsonl")
    first = append_record(store, "1")
    second = append_record(store, "2")
    lines = [json.loads(line) for line in store.path.read_text().splitlines()]
    assert first.previous_hash is None
    assert second.previous_hash == first.record_hash
    assert lines[1]["previous_hash"] == lines[0]["record_hash"]
    assert lines[0]["record_hash"] != lines[1]["record_hash"]


def test_empty_existing_evidence_file_starts_new_chain(tmp_path):
    path = tmp_path / "evidence.jsonl"
    path.write_text("")
    record = append_record(EvidenceStore(path))
    assert record.previous_hash is None


def test_invalid_existing_evidence_is_rejected(tmp_path):
    path = tmp_path / "evidence.jsonl"
    path.write_text("not-json\n")
    with pytest.raises(EvidenceError, match="invalid final record"):
        append_record(EvidenceStore(path))
    path.write_text(json.dumps({"record_hash": 123}) + "\n")
    with pytest.raises(EvidenceError, match="record hash is invalid"):
        append_record(EvidenceStore(path))
