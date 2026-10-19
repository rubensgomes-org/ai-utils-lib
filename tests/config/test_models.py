"""Tests for ai_utils_lib.config.models."""

from typing import Any

import pytest
from pydantic import ValidationError

from ai_utils_lib.config.models import Azure, Model

API_KEY_ENV = "TEST_API_KEY"
ENV_API_KEY = "env-secret"
EXPLICIT_API_KEY = "explicit-secret"


def _model(**fields: Any) -> Model:
    return Model.model_validate(
        {
            "base_url": "https://model.test/v1",
            "name": "test-model",
            "instructions": "Test instructions.",
            **fields,
        }
    )


@pytest.fixture(autouse=True)
def api_key_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(API_KEY_ENV, ENV_API_KEY)


def test_model_reads_api_key_from_env() -> None:
    assert _model(api_key_env=API_KEY_ENV).api_key == ENV_API_KEY


@pytest.mark.parametrize(
    "api_key_env_name", [API_KEY_ENV, None], ids=["with-env", "without-env"]
)
def test_model_keeps_explicit_api_key(api_key_env_name: str | None) -> None:
    model = _model(api_key_env=api_key_env_name, api_key=EXPLICIT_API_KEY)

    assert model.api_key == EXPLICIT_API_KEY


def test_model_leaves_api_key_unset_without_api_key_env() -> None:
    assert _model().api_key is None


def test_model_leaves_api_key_unset_when_env_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(API_KEY_ENV, "")

    assert _model(api_key_env=API_KEY_ENV).api_key is None


def test_model_rejects_attribute_assignment() -> None:
    model = _model()

    with pytest.raises(ValidationError):
        model.name = "other-model"


@pytest.mark.parametrize(
    "separator", ["app_config_separator", "secret_separator"]
)
def test_azure_rejects_empty_separator(separator: str) -> None:
    with pytest.raises(ValidationError):
        Azure.model_validate(
            {
                "app_config_prefix": "ai-utils/",
                "secret_prefix": "kv-prefix",
                separator: "",
            }
        )
