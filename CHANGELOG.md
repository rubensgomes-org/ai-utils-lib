# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `config.azure_load_config.aload_config`, an async `load_config` for callers
  with a running event loop.
- `config.config.aload_config`, an async `config.config.load_config`.
- `ai_utils_lib.config` exports `load_config` and `aload_config`.
- `scripts/tests/test_config.sh` exercises `load_config` and
  `aload_config` of `ai_utils_lib.config`.

### Changed

- **Breaking:** moved `ai_utils_lib.azure.config` to
  `ai_utils_lib.config.azure_load_config`.
- **Breaking:** moved `ai_utils_lib.config.file.config` to
  `ai_utils_lib.config.file_load_config`.
- **Breaking:** `config.azure_load_config.load_config` raises
  `RuntimeError`, not `KeyError`, when `KEY_VAULT_URI` is needed but not set.
- **Breaking:** `config.config.load_config` raises `RuntimeError`, not
  `KeyError`, when `APP_CONFIG_ENDPOINT` is set but `APP_ENV` is not set
  or is empty.
- **Breaking:** `config.azure_load_config.load_config` raises
  `ValueError` for an App Configuration setting with no value, instead of
  overriding the YAML value with `None`.
- `config.azure_load_config.load_config` ignores App Configuration
  `azure.app_config_prefix` and `azure.app_config_separator`, logging a
  warning when they differ from `config.yaml`.
- Renamed `scripts/tests/test_azure_config.sh` to
  `test_azure_load_config.sh`; it takes a `key_vault_uri` and reports the
  API key source.
- `scripts/tests/` scripts print their inputs and steps, show at most the
  last 4 characters of secrets, and `test_entra_id.sh` takes a `scope`.

### Removed

- The `__main__` block of `config.config`.

### Fixed

- `config.azure_load_config.load_config` escapes `*`, `,` and `\` in
  `app_config_prefix` when querying App Configuration.

## [0.0.8] - 2026-10-20

### Added

- `ai_token_provider` takes an optional `scope`; `AI_FOUNDRY_SCOPE`
  targets Azure AI Foundry project and Agent APIs.
- `scripts/tests/` scripts exercise the Azure modules against live
  resources, replacing their `__main__` blocks.

### Changed

- **Breaking:** the Azure modules moved from `ai_utils_lib.config.azure`
  to `ai_utils_lib.azure`.
- **Breaking:** renamed `token_provider` to `ai_token_provider`.
- **Breaking:** `list_settings` raises `ValueError` for a `label_filter`
  containing `*` or `,`.
- `read_secret` strips surrounding whitespace from the secret value, and
  raises `ValueError` for an invalid secret name before calling Key Vault.

### Fixed

- `read_secret` rejects whitespace-only secrets.

## [0.0.7] - 2026-10-19

### Added

### Changed

- The `mcp` and `web` config sections are optional; when omitted, `mcp`
  is empty and `web` uses its defaults.

### Fixed

## [0.0.6] - 2026-10-19

### Added

### Changed

- **Breaking:** config models are frozen; assigning an attribute raises
  `ValidationError`. Use `model_copy(update=...)` to derive a modified
  copy.
- Depend on `azure-appconfiguration` instead of
  `azure-appconfiguration-provider`.

### Fixed

- `Model` keeps an explicitly given `api_key` instead of overwriting it
  from `api_key_env`, so a `model/api_key` App Configuration setting
  now takes effect and Key Vault is skipped.
- The Azure loader appends `app_config_separator` to an
  `app_config_prefix` lacking it, so settings are no longer dropped and
  keys of sibling prefixes (e.g., `ai-utils-other/`) are no longer read.
- The Azure loader rejects setting keys with empty segments
  (e.g., `model//name`) instead of ignoring them.
- Empty `app_config_separator` and `secret_separator` values are rejected
  with a `ValidationError`, and the Azure loader validates the `azure`
  section before querying App Configuration.

## [0.0.5] - 2026-10-19

### Added

- `Azure.secret_separator`, defaulting to `--`.

### Changed

- The Azure loader reads `Model.api_key` from the Key Vault at
  `KEY_VAULT_URI`, in secret `secret_prefix` + `secret_separator` +
  `api_key_env`, with `_` replaced by `-`, unless the variable named by
  `api_key_env` holds the key.
- Breaking: `list_settings` and `read_secret` take an
  `AsyncTokenCredential` first argument, owned by the caller.
- Breaking: `secret_prefix` excludes the separator, and
  `app_config_prefix` must end with `app_config_separator`.
- Bundled `config.yaml`: `web.host` is `127.0.0.1`, and the `calculator`
  MCP server is `http://127.0.0.1:8080/mcp` without OAuth.

### Fixed

## [0.0.4] - 2026-10-19

### Added

### Changed

- `Model.api_key` is read from the environment variable named by
  `api_key_env`, and is None when either is unset or empty.
- `Model.api_key_env` accepts an empty string.

### Fixed

## [0.0.3] - 2026-10-19

### Added

### Changed

- `config.config` imports the Azure and file loaders as private
  `_load_azure_config` and `_load_file_config`.

### Fixed

## [0.0.2] - 2026-10-19

### Added

### Changed

- The `azure` section requires `app_config_prefix`; `app_config_separator`
  defaults to `/`.
- `mcp.<name>.token_dir` defaults to `~/.oauth_tokens`.

### Fixed

## [0.0.1] - 2026-10-19

### Added

- `load_config` and `configure_logging` load `config.yaml` from a package
  and apply its `logging` section.
- `list_settings` reads Azure App Configuration settings by key and label.
- `read_secret` reads a non-empty Azure Key Vault secret.
- `token_provider` returns an Entra ID token callable for the `api_key` of
  `openai.AsyncOpenAI`.
- `azure.config.load_config` overlays `config.yaml` with App Configuration
  settings under `azure.app_config_prefix`, split on
  `azure.app_config_separator`.
- `config.load_config` uses App Configuration when `APP_CONFIG_ENDPOINT` is
  set, labeled `APP_ENV`, and `config.yaml` alone otherwise.
- Unit tests for all modules, using `pytest-mock`.

### Changed

- Test coverage excludes `if __name__ == "__main__":` blocks.
- `read_yaml` and `resolve_config_path` in `file.config` are public.
- `scripts/initvars.sh` manages only the `PYPI_API_TOKEN` and `SONAR_TOKEN`
  secrets the workflows use, and deletes the Azure, Terraform and model API
  key variables and secrets it used to manage.

### Fixed
