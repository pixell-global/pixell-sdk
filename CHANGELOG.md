# Changelog

All notable changes to pixell-kit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of pixell-kit
- CLI commands: `pak init`, `pak build`, `pak run-dev`, `pak inspect`, `pak validate`
- Support for Python 3.11 and 3.12
- Agent manifest schema (`agent.yaml`)
- APKG packaging format
- Local development server with hot-reload
- Package validation and integrity checks
- Installation via pip, pipx, and Homebrew

### Security
- SHA-256 hash generation for packages
- Optional GPG signing support (future release)

## [0.1.0] - 2025-01-11

- Initial alpha release

[Unreleased]: https://github.com/pixell-global/pixell-kit/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/pixell-global/pixell-kit/releases/tag/v0.1.0