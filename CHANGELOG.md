# Changelog

All notable changes to this plugin are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow [Semantic Versioning](https://semver.org/). Merging to `master` publishes the plugin.

## [Unreleased]

## [0.1.3] - 2026-11-02

### Changed

- Skills call the connector's generation tools by task (`text2image`, `image2image`, `background_remove`, `text2video`, `image2video`, `reference2video`, `firstlast2video`, `video2video`) and pass the model as `model_id`, because the connector no longer lists one tool per model. The model each skill uses is unchanged.
- The quote that gates a run is `creagen_estimate_generation` for the exact tool, `model_id` and inputs, one per output. Its `prepared` result is submitted unchanged with a stable `request_id`. An uncertain submission is recovered with `creagen_get_generation_receipts` under the same key; a revision, regeneration or retry after a failure gets a new estimate and a new key. `creagen_estimate_credit` remains for general price questions.
- Results are presented when `check_generation_status` reports `COMPLETED` with `assetReady`. A `FAILED` status marked `retryable` or `requiresReauth`, or a `REQUEST_CONFLICT`, is checked again instead of regenerated.

### Removed

- Veo 3.1 first and last frame models, which the connector no longer offers. The first and last frame example is now Gemini Omni Flash.

## [0.1.2] - 2026-10-01

### Changed

- Codex listing metadata for directory review: the subtitle (`interface.shortDescription`) fits the 30-character limit, the category is Creativity, and the manifest declares the support page (`interface.supportURL`).

## [0.1.1] - 2026-09-30

### Added

- Pull request checks in GitHub Actions: manifest, skill, README, link, leak and changelog lint (`.github/scripts/check.py`) and the Claude plugin validator at a pinned version.
- Pull request template, issue chooser with a skill or plugin problem form, and Dependabot updates for GitHub Actions.
- `AGENTS.md` (imported for Claude Code by `.claude/CLAUDE.md`) with contributor rules for coding agents.
- This changelog.

### Security

- Skills treat tool results (designer output, journey guidance, command strings) as data and do not run commands from them. The one exception is the local file upload: the agent uploads only the file the user named, with `curl -X PUT -T <file> -H "Content-Type: <returned type>" <upload URL>`, built from the returned parts, after checking that it is an `https` URL on a Creagen or cloud-storage host.
- Skills estimate and ask again when anything that drives cost changes after approval, and cap automatic regeneration at two per deliverable, including new models, people and reference sheets.
- `creagen-product-detail-page` reviews the returned HTML before presenting it: no scripts, event handlers, frames, forms or other embedded content, and links and images only to generated public URLs, the designer's own font stylesheets, `#` links and placeholders.
- CI: more credential formats and look-alike spellings are caught by the leak scan; the workflow scan rejects escapes, aliases, extra documents and look-alike characters; `check.py selftest` keeps these bypasses covered.
- `SECURITY.md` points to GitHub private vulnerability reporting first; `.gitignore` covers more credential and key files.

### Changed

- README (all three languages) states that the only command the skills ask an agent to run is the file upload.
- Clarify in README and SECURITY.md that `.github/` holds CI lint only; the agent never loads it.
- CONTRIBUTING.md now covers running the checks, how releases work and what belongs in this repository.
- CI lint also checks workflow files (pinned `actions/*` only, read-only permissions, no secrets or `pull_request_target`), finds hostnames written without `https://`, and treats hostnames and long numbers in pull request text and commit messages as errors.

## [0.1.0] - 2026-09-30

### Added

- Creagen connector (`.mcp.json`).
- Skills: `creagen-generate`, `creagen-lookbook`, `creagen-product-detail-page`, `creagen-promo-video`, `creagen-ugc-video`.
- Claude plugin and marketplace manifests (`.claude-plugin/`), Codex plugin manifest (`.codex-plugin/`).
- README in English, Korean and Japanese; CONTRIBUTING and SECURITY policies.
