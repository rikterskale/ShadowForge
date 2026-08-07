import json

import pytest

from shadowforge.scope import EngagementScope, ScopeError


def test_scope_contains_subnets(tmp_path):
    path = tmp_path / "scope.json"
    path.write_text(json.dumps({"name": "lab", "targets": ["10.0.0.0/24"]}))
    scope = EngagementScope.from_file(path)
    assert scope.contains("10.0.0.5")
    assert scope.contains("10.0.0.128/25")
    assert not scope.contains("10.0.1.1")


def test_scope_handles_mixed_ip_families_in_any_order(tmp_path):
    path = tmp_path / "scope.json"
    path.write_text(
        json.dumps({"name": "mixed", "targets": ["2001:db8::/32", "192.0.2.0/24"]})
    )
    scope = EngagementScope.from_file(path)
    assert scope.contains("192.0.2.10")
    assert scope.contains("2001:db8::10")
    path.write_text(
        json.dumps({"name": "mixed", "targets": ["192.0.2.0/24", "2001:db8::/32"]})
    )
    scope = EngagementScope.from_file(path)
    assert scope.contains("192.0.2.10")
    assert scope.contains("2001:db8::10")


def test_scope_rejects_bad_files_and_non_string_targets(tmp_path):
    path = tmp_path / "scope.json"
    path.write_text("{}")
    with pytest.raises(ScopeError, match="non-empty string 'name'"):
        EngagementScope.from_file(path)
    path.write_text(json.dumps({"name": "   ", "targets": ["192.0.2.1"]}))
    with pytest.raises(ScopeError, match="non-empty string 'name'"):
        EngagementScope.from_file(path)
    path.write_text(json.dumps({"name": "x", "targets": []}))
    with pytest.raises(ScopeError, match="non-empty 'targets' list"):
        EngagementScope.from_file(path)
    path.write_text(json.dumps({"name": "x", "targets": [123]}))
    with pytest.raises(ScopeError, match="non-empty IP/CIDR string"):
        EngagementScope.from_file(path)
    path.write_text(json.dumps({"name": "x", "targets": [""]}))
    with pytest.raises(ScopeError, match="non-empty IP/CIDR string"):
        EngagementScope.from_file(path)
    path.write_text(json.dumps({"name": "x", "targets": ["bad"]}))
    with pytest.raises(ScopeError, match="invalid target"):
        EngagementScope.from_file(path)


def test_scope_name_is_trimmed(tmp_path):
    path = tmp_path / "scope.json"
    path.write_text(json.dumps({"name": "  lab  ", "targets": ["192.0.2.0/24"]}))
    scope = EngagementScope.from_file(path)
    assert scope.name == "lab"


def test_scope_requires_ip_or_cidr(tmp_path):
    path = tmp_path / "scope.json"
    path.write_text(json.dumps({"name": "lab", "targets": ["192.0.2.0/24"]}))
    scope = EngagementScope.from_file(path)
    with pytest.raises(ScopeError):
        scope.contains("example.com")
    with pytest.raises(ScopeError):
        scope.require("192.0.3.1")
