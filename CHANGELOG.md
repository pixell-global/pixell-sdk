# Changelog

All notable changes to pixell-kit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.4] - 2025-08-21

### Fixed
- Updated PyPI trusted publisher configuration documentation
- Version bump to resolve deployment issues

## [0.3.3] - 2025-08-21

### Added
- New `pixell guide` command to display build documentation in terminal
- Interactive guide accessible directly from CLI without needing external docs
- Support for topic-specific guides with --topic option

### Fixed
- Removed all unused imports to pass ruff linting
- Fixed mypy type errors for better type safety
- Ensured CI/CD passes on all operating systems (Linux, macOS, Windows)

## [0.3.0] - 2025-01-21

### Added
- Comprehensive Agent Developer Guide with detailed `pixell build` instructions
- Clear documentation for `agent.yaml` manifest structure and requirements
- Step-by-step build process explanation with validation rules
- Common build errors and solutions section
- Complete examples of agent configuration

### Improved
- Enhanced developer documentation for building agents
- Better guidance on project structure requirements
- Clearer explanation of required vs optional fields in agent.yaml

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

[Unreleased]: https://github.com/pixell-global/pixell-kit/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/pixell-global/pixell-kit/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/pixell-global/pixell-kit/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/pixell-global/pixell-kit/releases/tag/v0.1.0