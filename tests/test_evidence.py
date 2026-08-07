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


def test_evidence_records_are_hash_chained_and_verified(tmp_path):
    store = EvidenceStore(tmp_path / "evidence.jsonl")
    first = append_record(store, "1")
    second = append_record(store, "2")
    lines = [json.loads(line) for line in store.path.read_text().splitlines()]
    assert first.previous_hash is None
    assert second.previous_hash == first.record_hash
    assert lines[1]["previous_hash"] == lines[0]["record_hash"]
    assert lines[0]["record_hash"] != lines[1]["record_hash"]
    assert store.verify() == 2


def test_empty_or_missing_evidence_file_is_valid(tmp_path):
    missing = EvidenceStore(tmp_path / "missing.jsonl")
    assert missing.verify() == 0
    path = tmp_path / "evidence.jsonl"
    path.write_text("")
    store = EvidenceStore(path)
    assert store.verify() == 0
    record = append_record(store)
    assert record.previous_hash is None


def test_malformed_existing_evidence_is_rejected(tmp_path):
    path = tmp_path / "evidence.jsonl"
    path.write_text("not-json\n")
    store = EvidenceStore(path)
    with pytest.raises(EvidenceError, match="record 1 is malformed"):
        store.verify()
    with pytest.raises(EvidenceError, match="record 1 is malformed"):
        append_record(store)

    path.write_text(json.dumps({"record_hash": 123}) + "\n")
    with pytest.raises(EvidenceError, match="invalid record hash"):
        store.verify()


def test_tampered_record_contents_are_rejected_before_append(tmp_path):
    store = EvidenceStore(tmp_path / "evidence.jsonl")
    append_record(store, "1")
    record = json.loads(store.path.read_text())
    record["target"] = "198.51.100.99"
    store.path.write_text(json.dumps(record) + "\n")
    with pytest.raises(EvidenceError, match="hash does not match"):
        store.verify()
    with pytest.raises(EvidenceError, match="hash does not match"):
        append_record(store, "2")


def test_broken_previous_hash_link_is_rejected(tmp_path):
    store = EvidenceStore(tmp_path / "evidence.jsonl")
    append_record(store, "1")
    append_record(store, "2")
    records = [json.loads(line) for line in store.path.read_text().splitlines()]
    second = records[1]
    second["previous_hash"] = "0" * 64
    unsigned = {key: value for key, value in second.items() if key != "record_hash"}
    second["record_hash"] = store._hash_payload(unsigned)
    store.path.write_text("\n".join(json.dumps(item) for item in records) + "\n")
    with pytest.raises(EvidenceError, match="broken previous-hash link"):
        store.verify()
