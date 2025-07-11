# Changelog

All notable changes to pixell-kit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2025-01-11

### Added
- Fully implemented `pixell validate` command with comprehensive validation
- Fully implemented `pixell build` command to create APKG packages
- Fully implemented `pixell run-dev` command with development server
- Agent manifest validation using Pydantic models
- Development server with FastAPI for local testing
- File watching and hot-reload in development mode
- Colored CLI output for better user experience
- Proper error handling and informative error messages

### Fixed
- Fixed package installation to include all submodules
- Fixed pyproject.toml package configuration
- Corrected CLI command names from `pak` to `pixell`

### Changed
- Updated CLI commands to use `pixell` instead of `pak`

## [0.1.0] - 2025-01-11

### Added
- Initial release of pixell-kit
- Basic CLI structure with placeholder commands
- Support for Python 3.11 and 3.12
- Agent manifest schema (`agent.yaml`)
- APKG packaging format specification
- Installation via pip, pipx, and Homebrew

### Security
- SHA-256 hash generation for packages
- Optional GPG signing support (future release)

[Unreleased]: https://github.com/pixell-global/pixell-kit/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/pixell-global/pixell-kit/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/pixell-global/pixell-kit/releases/tag/v0.1.0