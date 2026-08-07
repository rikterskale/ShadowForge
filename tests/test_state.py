import json
from unittest.mock import patch

import pytest

from shadowforge.state import (
    EngagementState,
    EngagementStateStore,
    Observation,
    StateError,
)


def observation(step=1, tool="nmap_service_scan", target="192.0.2.10", status="ok", data=None):
    return {"step": step, "tool": tool, "target": target, "status": status, "data": data or {}}


def test_session_id_validation_and_path(tmp_path):
    store = EngagementStateStore(tmp_path)
    assert store.validate_session_id("engagement-01.alpha") == "engagement-01.alpha"
    assert store.path_for("engagement-01") == tmp_path / "engagement-01.json"


@pytest.mark.parametrize(
    "value",
    ["", "../escape", "/absolute", "has space", "x" * 65, None, "a/b"],
)
def test_session_id_rejects_unsafe_values(tmp_path, value):
    with pytest.raises(StateError, match="session must"):
        EngagementStateStore(tmp_path).validate_session_id(value)


def test_create_save_reload_and_planner_context(tmp_path):
    store = EngagementStateStore(tmp_path)
    state = store.load_or_create(
        session_id="lab-1",
        target="192.0.2.10",
        objective="  Inspect services  ",
    )
    assert state.objective == "Inspect services"
    store.append_result(
        state,
        step=1,
        tool="nmap_service_scan",
        target="192.0.2.10",
        status="ok",
        data={"services": [{"port": 80}], "ignored": "x"},
    )
    state.summary = "Observed HTTP"
    store.save(state)
    loaded = store.load_or_create(
        session_id="lab-1",
        target="192.0.2.10",
        objective="Inspect services",
    )
    assert loaded.summary == "Observed HTTP"
    assert loaded.observations[0].data == {"services": [{"port": 80}]}
    context = loaded.planner_context()
    assert context["session_id"] == "lab-1"
    assert context["observations_untrusted_data"][0]["tool"] == "nmap_service_scan"


def test_http_state_sanitization_removes_unknown_fields(tmp_path):
    store = EngagementStateStore(tmp_path)
    state = EngagementState("s1", "192.0.2.10", "Inspect HTTP")
    store.append_result(
        state,
        step=1,
        tool="http_metadata_probe",
        target="192.0.2.10",
        status="ok",
        data={
            "scheme": "https",
            "port": 443,
            "status_code": 200,
            "reason": "OK",
            "headers": {"server": "example"},
            "set-cookie": "secret=value",
            "authorization": "secret",
        },
    )
    assert "set-cookie" not in state.observations[0].data
    assert "authorization" not in state.observations[0].data


def test_unexpected_nmap_shape_is_reduced_to_error(tmp_path):
    store = EngagementStateStore(tmp_path)
    state = EngagementState("s1", "192.0.2.10", "Inspect")
    store.append_result(
        state,
        step=1,
        tool="nmap_service_scan",
        target="192.0.2.10",
        status="error",
        data={"services": "bad"},
    )
    assert state.observations[0].data == {"error": "unexpected Nmap result shape"}


def test_nmap_services_are_bounded(tmp_path):
    store = EngagementStateStore(tmp_path)
    state = EngagementState("s1", "192.0.2.10", "Inspect")
    services = [{"port": number} for number in range(300)]
    store.append_result(
        state,
        step=1,
        tool="nmap_service_scan",
        target="192.0.2.10",
        status="ok",
        data={"services": services},
    )
    assert len(state.observations[0].data["services"]) == 256


@pytest.mark.parametrize(
    "kwargs,match",
    [
        ({"tool": "shell"}, "not permitted"),
        ({"target": "192.0.2.11"}, "target"),
        ({"status": "unknown"}, "status"),
        ({"step": 2}, "step must be 1"),
    ],
)
def test_invalid_new_observations_are_rejected(tmp_path, kwargs, match):
    store = EngagementStateStore(tmp_path)
    state = EngagementState("s1", "192.0.2.10", "Inspect")
    values = {
        "step": 1,
        "tool": "nmap_service_scan",
        "target": "192.0.2.10",
        "status": "ok",
        "data": {"services": []},
    }
    values.update(kwargs)
    with pytest.raises(StateError, match=match):
        store.append_result(state, **values)


def test_observation_limit_is_enforced(tmp_path):
    store = EngagementStateStore(tmp_path)
    observations = [
        Observation(number, "nmap_service_scan", "192.0.2.10", "ok", {})
        for number in range(1, 101)
    ]
    state = EngagementState("s1", "192.0.2.10", "Inspect", observations)
    with pytest.raises(StateError, match="limit"):
        store.append_result(
            state,
            step=101,
            tool="nmap_service_scan",
            target="192.0.2.10",
            status="ok",
            data={"services": []},
        )


def test_existing_session_cannot_be_rebound(tmp_path):
    store = EngagementStateStore(tmp_path)
    store.save(EngagementState("s1", "192.0.2.10", "Inspect"))
    with pytest.raises(StateError, match="bound to target"):
        store.load_or_create(session_id="s1", target="192.0.2.11", objective="Inspect")
    with pytest.raises(StateError, match="objective"):
        store.load_or_create(session_id="s1", target="192.0.2.10", objective="Different")


def test_malformed_json_is_rejected(tmp_path):
    store = EngagementStateStore(tmp_path)
    path = store.path_for("s1")
    path.parent.mkdir(parents=True)
    path.write_text("not-json")
    with pytest.raises(StateError, match="could not read"):
        store.load_or_create(session_id="s1", target="192.0.2.10", objective="Inspect")


def valid_payload():
    return {
        "version": 1,
        "session_id": "s1",
        "target": "192.0.2.10",
        "objective": "Inspect",
        "observations": [],
        "summary": None,
    }


@pytest.mark.parametrize(
    "mutator,match",
    [
        (lambda p: p.pop("summary"), "invalid schema"),
        (lambda p: p.update(version=2), "unsupported"),
        (lambda p: p.update(target=""), "target"),
        (lambda p: p.update(objective=""), "objective"),
        (lambda p: p.update(summary=42), "summary"),
        (lambda p: p.update(summary="x" * 2001), "summary"),
        (lambda p: p.update(observations="bad"), "bounded list"),
        (lambda p: p.update(observations=[{}]), "invalid schema"),
        (
            lambda p: p.update(observations=[observation(step=True)]),
            "invalid field types",
        ),
        (
            lambda p: p.update(observations=[observation(step=2)]),
            "contiguous",
        ),
        (
            lambda p: p.update(observations=[observation(target="192.0.2.11")]),
            "does not match",
        ),
        (
            lambda p: p.update(observations=[observation(status="unknown")]),
            "invalid status",
        ),
        (
            lambda p: p.update(observations=[observation(tool="shell")]),
            "not permitted",
        ),
    ],
)
def test_state_schema_validation(mutator, match):
    payload = valid_payload()
    mutator(payload)
    with pytest.raises(StateError, match=match):
        EngagementStateStore._parse(payload)


def test_loaded_http_state_is_resanitized():
    payload = valid_payload()
    payload["observations"] = [
        observation(
            tool="http_metadata_probe",
            data={
                "scheme": "http",
                "port": 80,
                "headers": {"server": "example"},
                "set-cookie": "secret=value",
            },
        )
    ]
    state = EngagementStateStore._parse(payload)
    assert "set-cookie" not in state.observations[0].data


def test_state_observation_count_is_bounded():
    payload = valid_payload()
    payload["observations"] = [observation(step=index + 1) for index in range(101)]
    with pytest.raises(StateError, match="bounded list"):
        EngagementStateStore._parse(payload)


def test_save_wraps_write_errors_and_cleans_temp(tmp_path):
    store = EngagementStateStore(tmp_path)
    state = EngagementState("s1", "192.0.2.10", "Inspect")
    with (
        patch("pathlib.Path.write_text", side_effect=OSError("disk full")),
        pytest.raises(StateError, match="disk full"),
    ):
        store.save(state)


def test_load_wraps_read_oserror(tmp_path):
    store = EngagementStateStore(tmp_path)
    path = store.path_for("s1")
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(valid_payload()))
    with (
        patch("pathlib.Path.read_text", side_effect=OSError("unreadable")),
        pytest.raises(StateError, match="unreadable"),
    ):
        store.load_or_create(session_id="s1", target="192.0.2.10", objective="Inspect")
