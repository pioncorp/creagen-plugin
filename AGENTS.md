This file is for contributors to the creagen-plugin repository only.

# Agent guide

- This repository holds instruction text and manifests only. Do not add runnable files outside `.github/`.
- After any change run `python3 .github/scripts/check.py --all` (needs python3, plus Node 22 for the Claude validator; add `--no-claude` to skip it) and paste its last line in the pull request.
- Do not rely on `claude plugin validate` pointed at the repository root: it checks only marketplace.json. The script validates each manifest file explicitly.
- README.md, README.ko.md and README.ja.md change together.
- User-visible change: bump `version` in all three manifests and move the CHANGELOG notes under a new `## [x.y.z] - date` heading. Otherwise add a line under `## [Unreleased]`.
- Skills may name only tools and input fields that the Creagen connector actually lists. Do not invent options.
- Preserve exact credit estimates, the user's approval scope, stable request keys, receipt recovery, and successful item completion before delivery. Each skill contains one copy of `.github/templates/generation-protocol.md`; edit the template and all copies together. Do not replace this contract with a tool-name mention or treat receipt completion as item success.
- No prompt-injection-style wording (steering the agent toward or away from particular tools, pulling in instructions from a URL), no promotional comparisons, no third-party logo badges.
- No secrets, internal hostnames, private repository paths, account identifiers or personal data. The host allowlist in `.github/scripts/check.py` is the rule, for links and for plain-text hostnames alike. Pull request titles and descriptions and commit messages are scanned like files.
- Workflows (`.github/workflows/`): only `actions/*` actions pinned to a full commit SHA, top-level `permissions: contents: read`, no secrets, no `pull_request_target` or `workflow_run`, no `${{ }}` inside `run:` scripts. Write plain block YAML; `check.py` reads it line by line.
- Open pull requests only: `master` is protected and merging it publishes the plugin.
- Details and rationale: `CONTRIBUTING.md`.
