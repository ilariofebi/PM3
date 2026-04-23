# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-04-23

### Added
- Database backup system with gzip compression and backup rotation.
- Startup JSON database validation with recovery hints for restore.
- Configurable log rotation and optional compression for process logs.
- New `config.ini.sample` with implemented settings.
- `DAEMON_DB_CORRUPTED` exit code for corrupted database startup path.

### Changed
- Improved process-tree termination flow: SIGTERM, SIGKILL fallback, zombie cleanup.
- Improved local process kill flow with graceful terminate/wait before hard kill.
- Updated dependency minimums for `psutil` and `tinydb`.
- Added `filelock` dependency explicitly in requirements.
- Version bumped to `0.5.0`.

### Fixed
- Corrected `stderr` default path handling in process formatter.
- Removed lock debug `print()` noise and replaced with structured logging.

## [0.3.28] - 2026-04-23

### Added
- `pm3 version` command.

## [0.3.27] - 2026-04-23

### Added
- TinyDB file lock system to avoid JSON corruption in multi-threaded operations.
