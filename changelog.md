# Changelog

All notable changes to ZipInstaller Modern will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Automatic update checking
- Support for other archives (7z, rar)
- Ability to force language

## [0.9.3] - 2025-11-06

### Added
- Initial release of ZipInstaller Modern
- ZIP file installation with automatic executable detection
- Metadata extraction from Windows executables (version, publisher, icon)
- Smart ZIP structure detection (root or first subdirectory)
- Complete uninstallation with additional files detection
- Windows Registry integration (Add/Remove Programs)
- Desktop and Start Menu shortcut creation
- Context menu integration ("Install with ZIM...")
- Self-installation/uninstallation capability
- Auto-update detection for ZIM itself
- Dark mode theme support (follows Windows settings)
- Multi-language support (English and Spanish via Babel)
- Background installation with progress feedback
- Automatic version comparison and upgrade prompts
- Installation info JSON tracking
- Self-delete batch script for clean uninstallation

### Technical
- Built with PySide6 (Qt for Python)
- Uses pywin32 for Windows integration
- pefile for executable metadata parsing
- Compiled with Nuitka for standalone distribution
- GPLv3 licensed

### Dependencies
- PySide6 >= 6.6.0
- pywin32 >= 306
- pefile >= 2023.2.7
- pyshortcuts >= 1.9.1
- Babel >= 2.13.0

[Unreleased]: https://github.com/JMVS/zipinstaller-modern/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/JMVS/zipinstaller-modern/releases/tag/v1.0.0