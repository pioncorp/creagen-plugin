# Security Policy

## Reporting a vulnerability

Please report security issues privately. The preferred way is a GitHub private security advisory: [report a vulnerability](https://github.com/pioncorp/creagen-plugin/security/advisories/new). Only the maintainers can see it. If you cannot use GitHub, email **help@vcat.ai** with "Security" in the subject line. Do not open a public GitHub issue for security problems.

Include as much of the following as you can:

- A description of the issue and its impact.
- Steps to reproduce, or a proof of concept.
- The affected component: this plugin's files (skills, manifests, `.mcp.json`) or the Creagen connector and service.

We will acknowledge your report, investigate, and keep you informed of the outcome. Please give us reasonable time to fix the issue before disclosing it publicly.

## Scope

This repository contains only instruction text (skills) and manifests; agents never load executable code from it. The `.github/` directory holds CI lint and workflow files used only by GitHub Actions and contributors. Issues in the Creagen connector or service can be reported through the same address.

Please do not access other users' data, disrupt the service, or run automated scans that degrade it while testing.
