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


def test_scope_rejects_bad_files(tmp_path):
    path = tmp_path / "scope.json"
    path.write_text("{}")
    with pytest.raises(ScopeError):
        EngagementScope.from_file(path)
    path.write_text(json.dumps({"name": "x", "targets": []}))
    with pytest.raises(ScopeError):
        EngagementScope.from_file(path)
    path.write_text(json.dumps({"name": "x", "targets": ["bad"]}))
    with pytest.raises(ScopeError):
        EngagementScope.from_file(path)


def test_scope_requires_ip_or_cidr(tmp_path):
    path = tmp_path / "scope.json"
    path.write_text(json.dumps({"name": "lab", "targets": ["192.0.2.0/24"]}))
    scope = EngagementScope.from_file(path)
    with pytest.raises(ScopeError):
        scope.contains("example.com")
    with pytest.raises(ScopeError):
        scope.require("192.0.3.1")
