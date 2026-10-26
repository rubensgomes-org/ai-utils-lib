# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

- The `azure` section of `config.yaml` is optional, and `AppConfig.azure`
  defaults to `None`. `azure.azure_config.aload_config` raises `ValueError`
  without it.
- The `model` section of `config.yaml` is optional, and `AppConfig.model`
  defaults to `None`. `azure.azure_config.aload_config` skips Key Vault
  without it.

### Fixed

## [0.0.16] - 2026-10-26

### Added

- `AIClientManager.create_agent`, which creates a prompt agent version, and
  `AIClientManager.delete_agent`, which deletes an agent and all its versions.
- Optional `agent_input` parameter for
  `AIClientManager.post_conversation_to_agent`, defaulting to `""`.

### Changed

### Fixed

## [0.0.15] - 2026-10-25

### Added

- `foundry.client_mgr.AIClientManager`, which keeps Foundry project and
  OpenAI clients open between application startup and shutdown. It fetches
  agents and conversation items, adds conversation items, and posts
  conversations to server-side agents.

### Changed

### Fixed

## [0.0.14] - 2026-10-23

### Added

- Optional `foundry.resource_endpoint` setting, defaulting to `None`.

### Changed

### Fixed

## [0.0.13] - 2026-10-23

### Added

### Changed

- **Breaking:** `azure.azure_load_config` is renamed to `azure.azure_config`,
  and `file.file_load_config` to `file.file_config`.

### Fixed

## [0.0.12] - 2026-10-23

### Added

- `azure-core` dependency.

### Changed

- **Breaking:** the sync `config.load_config` and
  `config.azure_load_config.load_config` are removed; await
  `config.aload_config` instead.
- **Breaking:** `config.azure_load_config` moves to
  `azure.azure_load_config`, and its `aload_config` takes the YAML-loaded
  `AppConfig` instead of a path.
- **Breaking:** `config.models` moves to `config_models`, and
  `config.file_load_config` to `file.file_load_config`, whose `read_yaml`
  is private.
- **Breaking:** config models reject unknown keys, in `config.yaml` and in
  App Configuration.
- `azure.app_config_prefix` and `azure.app_config_separator` set in App
  Configuration are no longer ignored.
- The bundled `config.yaml` sets `web.host` to `0.0.0.0` and `web.port`
  to `8080`. `config/azure_appcs_config_<env>.yaml` no longer set `azure`,
  `web` or the `mcp` OAuth settings.
- `scripts/tests/test_config.sh` and `test_azure_load_config.sh` load with
  `aload_config`.

### Fixed

## [0.0.11] - 2026-10-23

### Added

### Changed

- `README.md` lists the Entra ID and Foundry utilities, notes active
  development, and shows the `openai` 3.37+ requirement.

### Fixed

## [0.0.10] - 2026-10-23

### Added

- `foundry.project_clients.get_ai_project_clients`, an async context
  manager yielding a Foundry `AIProjectClient` and its `AsyncOpenAI`
  client.
- `azure-ai-projects` and `openai` dependencies.
- Optional `foundry.agent_name` setting in `config.yaml`.
- `kv-create` and `kv-destroy` workflows that call the azure-iac workflows
  of the same name to provision and destroy the Key Vault and its
  dependencies.
- `config-app-import` and `config-app-delete` workflows that import and
  delete the `config/azure_appcs_config_<env>.yaml` settings in App
  Configuration under the `ai-utils-lib/` prefix.
- `key-vault-import` and `key-vault-delete` workflows that import and
  delete the `FOUNDRY-API-KEY`, `NVIDIA-API-KEY` and `OPENAI-API-KEY`
  secrets in Key Vault as `ai-utils-lib--<name>`.

### Changed

- `foundry.project_endpoint` is optional and defaults to `None`.
- The bundled `config.yaml` sets `azure.app_config_prefix` to
  `ai-utils-lib/` and `azure.secret_prefix` to `ai-utils-lib`.
- The bundled `config.yaml` and `config/azure_appcs_config_<env>.yaml` set
  `model.api_key_env` to `NVIDIA_API_KEY`.
- `scripts/initvars.sh` manages the Azure and `TF_VAR_*` Actions variables
  and the `AZURE_CLIENT_SECRET` secret used by the `kv-*` workflows, and
  the `FOUNDRY_API_KEY`, `NVIDIA_API_KEY` and `OPENAI_API_KEY` secrets
  used by `key-vault-import`.
- `scripts/tests/test_config.sh` and `test_azure_load_config.sh` take a
  `config.yaml` path instead of a package; `test_key_vault.sh` defaults to
  the `ai-utils-lib--NVIDIA-API-KEY` secret.
- SonarCloud also analyzes `.github`; `poe clean` removes `coverage.xml`.
- Raised the minimum versions of several dependencies.
- **Breaking:** moved the bundled `config.yaml` from `ai_utils_lib.config`
  to `ai_utils_lib`.
- **Breaking:** the `load_config` and `aload_config` functions take
  `config: Path`, the path to `config.yaml`, instead of `package: str`.
- **Breaking:** removed `file_load_config.resolve_config_path` and
  `constants.CONFIG_FILE_NAME`.

### Fixed

## [0.0.9] - 2026-10-20

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
