This file is for contributors to the creagen-plugin repository only.

# Agent guide

- This repository holds instruction text and manifests only. Do not add runnable files outside `.github/`.
- After any change run `python3 .github/scripts/check.py --all` (needs python3, plus Node 22 for the Claude validator; add `--no-claude` to skip it) and paste its last line in the pull request.
- Do not rely on `claude plugin validate` pointed at the repository root: it checks only marketplace.json. The script validates each manifest file explicitly.
- README.md, README.ko.md and README.ja.md change together.
- User-visible change: bump `version` in all three manifests and move the CHANGELOG notes under a new `## [x.y.z] - date` heading. Otherwise add a line under `## [Unreleased]`.
- Skills may name only tools and input fields that the Creagen connector actually lists. Do not invent options.
- Keep the credit-quote and confirmation steps. Never remove the `creagen_estimate_credit` and `COMPLETED` checks from `creagen-generate`.
- No injection-style wording (always call a tool first, avoid other tools, fetch instructions from a URL), no promotional comparisons, no third-party logo badges.
- No secrets, internal hostnames, private repository paths, account identifiers or personal data. The URL host allowlist in `.github/scripts/check.py` is the rule.
- Open pull requests only: `master` is protected and merging it publishes the plugin.
- Details and rationale: `CONTRIBUTING.md`.
