import pytest

from shadowforge.models import ModelError
from shadowforge.model_router import DEFAULT_MODELS, ModelRouter

ALL_MODELS = frozenset(DEFAULT_MODELS.values())
QWEN_ONLY = frozenset({"qwen3.5:27b"})


def test_router_matches_adatlas_models():
    assert DEFAULT_MODELS == {
        "primary": "qwen3.5:27b",
        "critic": "gemma4:31b",
        "coding": "devstral-small-2:24b",
    }
    router = ModelRouter()
    assert router.roles() == ("primary", "critic", "coding")
    assert router.provider_for("primary", ALL_MODELS).model == "qwen3.5:27b"
    assert router.provider_for("critic", ALL_MODELS).model == "gemma4:31b"
    assert router.provider_for("coding", ALL_MODELS).model == "devstral-small-2:24b"
    assert str(router.config_path()).endswith("config/models.yaml")


def test_qwen_only_falls_back_for_optional_roles():
    router = ModelRouter()
    statuses = {item.role: item for item in router.resolve(QWEN_ONLY)}
    assert statuses["primary"].active_model == "qwen3.5:27b"
    assert not statuses["primary"].fallback
    assert statuses["critic"].active_model == "qwen3.5:27b"
    assert statuses["critic"].fallback
    assert statuses["coding"].active_model == "qwen3.5:27b"
    assert statuses["coding"].fallback
    assert router.provider_for("critic", QWEN_ONLY).model == "qwen3.5:27b"
    assert router.provider_for("coding", QWEN_ONLY).model == "qwen3.5:27b"


def test_primary_qwen_is_required():
    with pytest.raises(ModelError, match="ollama pull qwen3.5:27b"):
        ModelRouter().resolve(frozenset({"gemma4:31b", "devstral-small-2:24b"}))


def test_router_rejects_unknown_role():
    with pytest.raises(KeyError):
        ModelRouter().provider_for("unknown", ALL_MODELS)
