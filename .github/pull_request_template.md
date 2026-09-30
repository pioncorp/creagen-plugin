## What / Why

<!-- One to three lines: what changes and why. -->

## Type

- [ ] Skill text
- [ ] Manifest
- [ ] Docs
- [ ] CI / chore

## Release impact

Merging to `master` publishes the plugin. See CONTRIBUTING.md, section Releases.

- [ ] User-visible: `version` bumped in all three manifests and `## [x.y.z] - date` added to CHANGELOG.md
- [ ] Not user-visible: one line under `## [Unreleased]` in CHANGELOG.md (or none for CI-only changes)

## Checklist

- [ ] `python3 .github/scripts/check.py --all` passes locally (paste the last line here)
- [ ] README.md, README.ko.md and README.ja.md changed together, or none of them
- [ ] Tool names and input fields used by skills exist in the current Creagen connector tool list (a maintainer confirms this; it cannot run in public CI because the connector needs sign-in)
- [ ] No secrets, internal hostnames, private paths, account identifiers or personal data
- [ ] No injection-style or promotional wording (see CONTRIBUTING.md)
- [ ] No third-party logo badges

Written with an AI agent? Name it (Claude Code / Codex / other):

Account, credits or connector sign-in problems: https://creagen.vcat.ai/help, not this repository.
