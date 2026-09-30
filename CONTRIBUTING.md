# Contributing

Thanks for your interest in improving the Creagen plugin for Claude.

## How to contribute

- All changes go through a pull request against `master`. Direct pushes are not accepted.
- Keep each pull request focused on one change, and describe what it changes and why.
- Run `claude plugin validate --strict .` before opening the pull request.

## Skills

- Each skill lives in `skills/<skill-name>/SKILL.md` with YAML front matter (`name`, `description`, `license`) followed by Markdown instructions.
- Skills are written in English only, because Claude reads them as instructions.
- Refer only to tools that the Creagen MCP server lists in `tools/list`, using their exact names and input fields. Do not describe tools or options that the server does not expose.
- Do not add prompt-injection-style wording: no instructions to always call a tool first, to avoid or override other tools or connectors, to fetch instructions from external sources, hidden or encoded instructions, or promotional copy.
- Ask for the user's confirmation before steps that spend Creagen credits.

## README translations

`README.md` (English) is the source of truth. `README.ko.md` (Korean) and `README.ja.md` (Japanese) must stay in sync with it: a pull request that changes one README must update all three, keeping the same structure, links, and facts.

## Security

Please report security issues privately as described in [SECURITY.md](SECURITY.md), not in a public issue or pull request.
