import pytest

from shadowforge.model_router import DEFAULT_MODELS, ModelRouter


def test_router_matches_adatlas_models():
    assert DEFAULT_MODELS == {
        "primary": "qwen3.5:27b",
        "critic": "gemma4:31b",
        "coding": "devstral-small-2:24b",
    }
    router = ModelRouter()
    assert router.roles() == ("primary", "critic", "coding")
    assert router.provider_for("primary").model == "qwen3.5:27b"
    assert router.provider_for("critic").model == "gemma4:31b"
    assert router.provider_for("coding").model == "devstral-small-2:24b"
    assert str(router.config_path()).endswith("config/models.yaml")


def test_router_rejects_unknown_role():
    with pytest.raises(KeyError):
        ModelRouter().provider_for("unknown")
