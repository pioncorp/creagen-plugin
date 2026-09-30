# Changelog

All notable changes to this plugin are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow [Semantic Versioning](https://semver.org/). Merging to `master` publishes the plugin.

## [Unreleased]

### Added

- Pull request checks in GitHub Actions: manifest, skill, README, link, leak and changelog lint (`.github/scripts/check.py`) and the Claude plugin validator at a pinned version.
- Pull request template, issue chooser with a skill or plugin problem form, and Dependabot updates for GitHub Actions.
- `AGENTS.md` (imported for Claude Code by `.claude/CLAUDE.md`) with contributor rules for coding agents.
- This changelog.

### Changed

- Clarify in README and SECURITY.md that `.github/` holds CI lint only; the agent never loads it.
- CONTRIBUTING.md now covers running the checks, how releases work and what belongs in this repository.

## [0.1.0] - 2026-09-30

### Added

- Creagen connector (`.mcp.json`).
- Skills: `creagen-generate`, `creagen-lookbook`, `creagen-product-detail-page`, `creagen-promo-video`, `creagen-ugc-video`.
- Claude plugin and marketplace manifests (`.claude-plugin/`), Codex plugin manifest (`.codex-plugin/`).
- README in English, Korean and Japanese; CONTRIBUTING and SECURITY policies.
