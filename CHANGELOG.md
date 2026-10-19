# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
