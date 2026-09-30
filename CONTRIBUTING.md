# Contributing

Thanks for your interest in improving the Creagen plugin for Claude, Codex, and other MCP-capable agents.

## How to contribute

- All changes go through a pull request against `master`. Direct pushes are not accepted. A pull request needs green CI and one approving review.
- Keep each pull request focused on one change, and describe what it changes and why.
- Run `python3 .github/scripts/check.py --all` before opening the pull request. It runs the same checks as CI. It needs python3, and Node 22 for the Claude validator (use `--no-claude` to skip that part). Paste its final line into the pull request.
- Keep the shared fields (name, version, license, author, URLs) of the three manifests (`.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json`) consistent, and bump all three versions together for user-visible changes. The descriptions are written separately for Claude and Codex.
- You can additionally run the plugin validator bundled with the Codex app (optional).
- If you wrote the change with an AI agent, say which one in the pull request template.

## Releases

Merging to `master` publishes the plugin: the Claude directory and marketplace read `master`.

- A change is user-visible when it alters skill wording in a way that changes behaviour, manifest fields, or README usage instructions. Bump `version` in all three manifests together, and in the same pull request move the `## [Unreleased]` notes of `CHANGELOG.md` under a new `## [x.y.z] - YYYY-MM-DD` heading.
- Typo, clarification and CI changes need only a line under `## [Unreleased]` (or nothing, for CI-only changes).
- CI rejects a version bump without a matching changelog entry, and rejects a version that goes backwards.
- The Claude validator version used by CI is pinned in `.github/claude-code-version`. A weekly job tries the latest validator; if it fails, update that file in a pull request that explains the new rule.

## Skills

- Each skill lives in `skills/<skill-name>/SKILL.md` with YAML front matter followed by Markdown instructions. The front matter keys are exactly `name`, `description` and `license`, and `name` must equal the directory name. Versions live in the manifests, not in skills.
- Skills are written in English only, because agents read them as instructions. The same `skills/` directory is loaded by both `.claude-plugin/` and `.codex-plugin/`.
- Refer only to tools that the Creagen MCP server lists in `tools/list`, using their exact names and input fields. Do not describe tools or options that the server does not expose. CI cannot check this, because the connector needs sign-in, so a maintainer confirms it during review.
- Do not add prompt-injection-style wording: no instructions to always call a tool first, to avoid or override other tools or connectors, to fetch instructions from external sources, hidden or encoded instructions, or promotional copy.
- Ask for the user's confirmation before steps that spend Creagen credits, and keep the credit-quote and confirmation steps of the existing skills.
- The validator that agents load accepts a wrong skill name or a missing license, so the check script is what catches those.

## README translations

`README.md` (English) is the source of truth. `README.ko.md` (Korean) and `README.ja.md` (Japanese) must stay in sync with it: a pull request that changes one README must update all three, keeping the same structure, links, and facts. CI checks the structure across the three files (links, code blocks, badges, language switcher); reviewers check the meaning.

## Repository layout

Only Markdown, JSON, YAML, PNG and the `.github/` tooling live here.

- Do not add runnable files outside `.github/`.
- `.claude/CLAUDE.md` only imports `AGENTS.md` for Claude Code. Keep it there: a `CLAUDE.md` at the repository root fails the plugin validator, and `.claude/` holds nothing else.
- Do not add internal hostnames, paths of other repositories, account identifiers or operational procedures.
- URL hosts must be in the allowlist at the top of `.github/scripts/check.py`. If your change needs a new host, add it in your pull request and explain why.
- Badges are text only; third-party logo badges are not accepted.

## Labels

| Label | Use |
|---|---|
| `type:feat`, `type:fix`, `type:chore` | Kind of change on a pull request |
| `bug` | Something is not working |
| `enhancement` | New feature or request |
| `documentation` | Documentation only |
| `good first issue` | Good for newcomers |
| `help wanted` | Extra attention is needed |
| `question` | Further information is requested |

## Security

Please report security issues privately as described in [SECURITY.md](SECURITY.md), not in a public issue or pull request.
