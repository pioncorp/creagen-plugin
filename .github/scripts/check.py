"""Repository lint for the Creagen plugin. Python 3.9+, standard library only.

This repository ships instruction text (skills), manifests and READMEs. Merging
to `master` publishes it, so the same checks run in CI before every merge and
can be reproduced locally with the same commands. This file lives under
`.github/` so the folders an agent loads (skills, manifests) stay free of
executable files.

Usage, from anywhere inside a checkout:

    python3 .github/scripts/check.py --all               # every check, including the Claude validator
    python3 .github/scripts/check.py --all --no-claude   # skip the Node-based validator
    python3 .github/scripts/check.py <subcommand>        # json manifests skills readme links leaks
                                                         # changelog tree workflows version [--print] validate

Pull-request context (what CI passes; set the same variables to reproduce it):

    git fetch origin master
    EVENT=pull_request BASE_REF=origin/master \\
        python3 .github/scripts/check.py --all --no-claude --git-range origin/master...HEAD

    EVENT      pull_request | push | anything else   (changelog rules need pull_request)
    BASE_REF   e.g. origin/master                    (changelog and README-together rules)
    PR_TITLE, PR_BODY                                (scanned by `leaks`; empty means skipped)
    PR_AUTHOR  login of the pull request author      (leaks: text of dependabot[bot] only warns about
                                                      hosts and long numbers, it quotes release notes)
    CLAUDE_CODE_VERSION                              (validate: overrides .github/claude-code-version)

Output contract. Every finding is one line, `path:line: RULE: message` for an
error and `path:line: warn RULE: message` for a warning. Nothing that a rule
matched is ever printed (CI logs are public), so messages only say how to fix
the problem; open the file at the reported line. Exit status is 1 when there is
at least one error, otherwise 0. The last line is `check.py: ALL OK` or
`check.py: N error(s), M warning(s)`.

Why each check exists:

    json       a broken manifest only shows up when someone installs the plugin
    manifests  three manifests share one identity; drift breaks listings and installs;
               no hooks or inline servers (the connector lives in .mcp.json)
    skills     the Claude validator accepts a wrong skill name or a missing license
    readme     the three translations must keep links, code, badges and switcher in sync
    links      relative links must resolve with exact case (macOS ignores case)
    leaks      the repository is public: host allowlist (a name without https:// counts too) and
               email allowlist, no secrets, identifiers, injection-style or promotional wording;
               commit messages and the pull request title and description follow the same rules
    changelog  a release needs a changelog entry and versions never go backwards
    tree       the public promise is text only; runnable files live only under .github/
    workflows  a merged workflow runs with the repository's trust: only actions/* pinned to a
               commit SHA, a read-only token, no secrets, no pull_request_target or workflow_run,
               no expressions inside run scripts
    selftest   known bypasses of the leak and workflow rules must stay rejected (regression cases)
    version    print the shared manifest version for scripts
    validate   run Anthropic's validator on each manifest file (pinned version)

To allow another URL host or email address, edit the ALLOWED_* constants below
and say why in the pull request.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlsplit

# ---------------------------------------------------------------------------
# Configuration. Edit the ALLOWED_* sets here, and explain the reason in the PR.
# ---------------------------------------------------------------------------
ALLOWED_HOSTS = {
    "creagen.vcat.ai",
    "vcat.ai",
    "agent.vcat.ai",
    "img.shields.io",
    "keepachangelog.com",
    "semver.org",
}
# github.com is allowed only under these path prefixes (no other organisation or repository).
ALLOWED_GITHUB_PREFIXES = {"/pioncorp/creagen-plugin"}
ALLOWED_EMAILS = {"help@vcat.ai"}
MCP_HOST = "agent.vcat.ai"

# Accepted only in commit messages and pull-request text (never in files):
# service addresses that tools add as trailers, and agent attribution links.
MESSAGE_ONLY_EMAILS = {"noreply@anthropic.com", "noreply@github.com", "support@github.com"}
MESSAGE_ONLY_HOSTS = {"claude.com"}
NOREPLY_RE = re.compile(r"@users\.noreply\.github\.com$")

# A name written without https:// (a dashboard, a chat workspace) is read as a host only when it
# ends in one of these suffixes; file names such as SKILL.md or check.py never match. Add a suffix
# here when a leak of that kind slips through.
BARE_HOST_TLDS = {
    "ai", "app", "cloud", "co", "com", "corp", "dev", "home", "internal", "intranet", "io", "jp",
    "kr", "lan", "local", "net", "org", "private", "xyz",
}
# Public product and service names that prose may write as a bare hostname; they are never allowed as a link.
TEXT_ONLY_HOSTS = {"claude.ai", "shields.io"}
# Pull-request text written by these bots quotes upstream release notes (links to other
# projects, commit numbers), so hosts and long numbers in it stay warnings.
BOT_AUTHORS = {"dependabot[bot]"}

MANIFESTS = [
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    ".codex-plugin/plugin.json",
]
P_CLAUDE, P_MARKET, P_CODEX = MANIFESTS
MCP_JSON = ".mcp.json"
READMES = ["README.md", "README.ko.md", "README.ja.md"]
LANG_NAMES = {"README.md": "English", "README.ko.md": "한국어", "README.ja.md": "日本語"}
VALIDATE_TARGETS = [".claude-plugin/plugin.json", ".claude-plugin/marketplace.json"]
VERSION_PIN_FILE = ".github/claude-code-version"

TEXT_EXT = {".md", ".json", ".yml", ".yaml", ".py", ".sh", ""}
BINARY_EXT = {".png"}
RUNNABLE_EXT = {
    ".py", ".sh", ".bash", ".zsh", ".js", ".mjs", ".cjs", ".ts", ".rb", ".go",
    ".pl", ".ps1", ".bat", ".cmd",
}
ROOT_ALLOWED = {
    ".claude", ".claude-plugin", ".codex-plugin", ".github", ".mcp.json", ".gitignore", "skills",
    "assets", "README.md", "README.ko.md", "README.ja.md", "CONTRIBUTING.md",
    "SECURITY.md", "CHANGELOG.md", "LICENSE", "AGENTS.md",
}
EXEC_ALLOWED_PREFIX = ".github/scripts/"
CLAUDE_DIR_ALLOWED = {".claude/CLAUDE.md"}
ASSET_MAX_BYTES = 200 * 1024
CREDIT_GUARD_SKILL = "creagen-generate"
CREDIT_GUARD_TOKENS = ("creagen_estimate_credit", "COMPLETED")

ROOT = Path(__file__).resolve().parents[2]
SELF = ".github/scripts/check.py"

# ---------------------------------------------------------------------------
# Regular expressions
# ---------------------------------------------------------------------------
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
URL_RE = re.compile(r"https?://[^\s<>\"'`)\]]+", re.I)
README_URL_RE = re.compile(r"https?://[^\s)\"'<>`]+")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
LOCAL_WORD_RE = re.compile(r"\b(?:localhost|127\.0\.0\.1|0\.0\.0\.0)\b", re.I)
LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
NUM_ID_RE = re.compile(r"(?<![#\w])\d{6,}(?![\w])")
# A dotted name that stands alone (ASCII boundaries, so a Korean or Japanese particle after it is fine),
# optionally followed by a path. The last label must be letters; BARE_HOST_TLDS decides what counts.
# Email addresses are blanked before this runs, so a name right after an @ is a stray mention.
BARE_HOST_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])((?:[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?\.)+[A-Za-z]{2,})"
    r"(?![A-Za-z0-9_-]|\.[A-Za-z0-9])(/[^\s<>\"'`)\]]*)?"
)
SECRET_RES = [
    re.compile(p, re.I if ci else 0)
    for p, ci in (
        (r"\bsk-[A-Za-z0-9_-]{20,}", False),  # OpenAI and Anthropic style keys, hyphens included
        (r"\b(?:sk|rk|pk)_(?:live|test)_[A-Za-z0-9]{16,}", False),
        (r"\bgh[oprsu]_[A-Za-z0-9]{30,}", False),
        (r"\bgithub_pat_[A-Za-z0-9_]{20,}", False),
        (r"\bglpat-[A-Za-z0-9_-]{20,}", False),
        (r"\bnpm_[A-Za-z0-9]{30,}", False),
        (r"\b(?:AKIA|ASIA)[0-9A-Z]{16}", False),
        (r"\bAIza[0-9A-Za-z_-]{35}", False),
        (r"\bxox[baprs]-[A-Za-z0-9-]{10,}", False),
        (r"\bxapp-[A-Za-z0-9-]{10,}", False),
        (r"-----BEGIN [A-Z ]*PRIVATE KEY", False),
        (r"\b(?:bearer|basic|token) [A-Za-z0-9._~+/=-]{20,}", True),
        (r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}", False),
        (r"://[^/\s:@]+:[^/\s@]+@", False),  # credentials inside a URL
        # A named credential assigned a long literal value (placeholders such as <token> or ${VAR} do not match).
        (r"(?:api[_-]?key|secret|token|passw(?:or)?d|credential)s?[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9/+_~.-]{24,}", True),
    )
]
# Characters that split or hide a token without changing how it reads.
INVISIBLE_RE = re.compile("[\u00ad\u200b-\u200f\u2060-\u2064\ufeff]")
INJECTION_RES = [
    re.compile(p, re.I)
    for p in (
        r"\balways (?:call|use|run|invoke)\b",
        r"\b(?:call|use|invoke) \S+ (?:first|before anything)",
        r"\bbefore (?:using |calling )?(?:any|all) other (?:tools?|connectors?|plugins?)",
        r"\bignore (?:all |any )?(?:previous|prior|other) (?:instructions|tools)",
        r"\bdo not use (?:any )?other (?:tools?|connectors?|plugins?)",
        r"\bfetch(?:ing)? .{0,40}instructions from\b",
        r"\bfollow (?:the )?instructions (?:at|from) https?://",
        r"[A-Za-z0-9+/]{48,}={0,2}",
    )
]
PROMO_RES = [
    re.compile(
        r"(?<!\w)(?:the )?(?:best|most reliable|#1|number one|top) (?:ai )?"
        r"(?:tool|plugin|connector|generator)s?\b",
        re.I,
    ),
    re.compile(r"\brecommended over\b", re.I),
    re.compile(r"\b(?i:better) than (?-i:[A-Z])[\w-]+"),
]
# `[/][/]` keeps this pattern from looking like a URL to the leak scan of this very file.
SHIELDS_IMG_RE = re.compile(r'<img\b[^>]*?\bsrc="(https:[/][/]img\.shields\.io/[^"]+)"')
BADGE_LOGO_RE = re.compile(r"img\.shields\.io/[^\s)\"'<>`]*[?&]logo\w*=", re.I)

FENCE_OPEN_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
FENCE_CLOSE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})\s*$")
INLINE_CODE_RE = re.compile(r"(`+)(.+?)\1")
MD_LINK_RE = re.compile(r"\]\(\s*<?([^)\s<>]*)>?(?:\s+(?:\"[^\"]*\"|'[^']*'))?\s*\)")
HTML_ATTR_RE = re.compile(r"""\b(href|src|srcset)\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.I)
REF_DEF_RE = re.compile(r"^ {0,3}\[[^\]]+\]:\s*<?(\S+?)>?(?:\s+.*)?$")
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
HEADING_RE = re.compile(r"^ {0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
FM_LINE_RE = re.compile(r"^([a-z]+):\s*(.*)$")
SKILL_NAME_RE = re.compile(r"^creagen-[a-z0-9]+(-[a-z0-9]+)*$")
CL_RELEASE_RE = re.compile(r"^## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})$")
VERSION_PIN_RE = re.compile(r"^(?:latest|\d+\.\d+\.\d+(?:-[0-9A-Za-z.]+)?)$")

# Workflow files are read line by line (no YAML parser: standard library only), so the rules
# below cover plain block YAML and anything they cannot read is rejected instead of skipped.
WORKFLOW_PATH_RE = re.compile(r"^\.github/workflows/[^/]+\.ya?ml$")
WORKFLOW_ACTION_RE = re.compile(r"^actions/[A-Za-z0-9._-]+(?:/[A-Za-z0-9._/-]+)?@[0-9a-f]{40}$")
WORKFLOW_TRIGGER_RE = re.compile(r"\b(?:pull_request_target|workflow_run)\b")
WORKFLOW_SECRETS_RE = re.compile(r"\bsecrets\b|\bgithub\s*(?:\.|\[\s*[\"'])\s*token\b", re.I)
# YAML spellings that hide a key or value from a line-by-line reader: double-quoted escapes,
# anchors, aliases, tags, complex keys, merge keys and extra documents.
WORKFLOW_ESCAPE_RE = re.compile(r"\\(?:[ux][0-9A-Fa-f]|[0-7])")
WORKFLOW_INDIRECT_RE = re.compile(r"""^\s*(?:-\s+)*(?:(?:[^\s:#][^:#]*)?:\s+)?(?:[&*]\S|![!<A-Za-z]|\?(?:\s|$))|^\s*(?:-\s+)*["']?<<["']?\s*:""")
WORKFLOW_DOC_RE = re.compile(r"^(?:---|\.\.\.)(?:\s|$)")
WORKFLOW_KEY_RE = re.compile(r"""^(\s*(?:-\s+)*)["']?([A-Za-z_][\w-]*)["']?\s*:(?:\s+(.*))?$""")
WORKFLOW_FLOW_RE = re.compile(r"""[{,]\s*["']?(?:uses|run|script|permissions)["']?\s*:""")
WORKFLOW_PERM_ITEM_RE = re.compile(r"""^\s+["']?([A-Za-z-]+)["']?\s*:\s*["']?([A-Za-z-]+)["']?$""")


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------
class Report:
    """Collects findings; identical findings are reported once."""

    def __init__(self) -> None:
        self.items: list[tuple] = []
        self._seen: set = set()

    def _add(self, severity: str, path: str, line: int, rule: str, message: str) -> None:
        key = (severity, path, max(int(line), 1), rule, message)
        if key not in self._seen:
            self._seen.add(key)
            self.items.append(key)

    def error(self, path: str, line: int, rule: str, message: str) -> None:
        self._add("error", path, line, rule, message)

    def warn(self, path: str, line: int, rule: str, message: str) -> None:
        self._add("warn", path, line, rule, message)


def counts(items) -> tuple[int, int]:
    errors = sum(1 for item in items if item[0] == "error")
    return errors, len(items) - errors


def render(item: tuple) -> str:
    severity, path, line, rule, message = item
    tag = "" if severity == "error" else "warn "
    return f"{path}:{line}: {tag}{rule}: {message}"


# ---------------------------------------------------------------------------
# Repository access
# ---------------------------------------------------------------------------
class GitError(Exception):
    pass


def git(*args: str) -> str:
    try:
        proc = subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True)
    except OSError as exc:  # git missing
        raise GitError(str(exc)) from exc
    if proc.returncode != 0:
        raise GitError(proc.stderr.decode("utf-8", "replace").strip())
    return proc.stdout.decode("utf-8", "replace")


_files_cache: list[str] | None = None
_text_cache: dict[str, str] = {}
_json_cache: dict[str, object] = {}


def repo_files() -> list[str]:
    """Tracked files plus untracked files that are not ignored (what `git add -A` would add)."""
    global _files_cache
    if _files_cache is None:
        out = git("ls-files", "-z", "--cached", "--others", "--exclude-standard")
        names = {n for n in out.split("\0") if n}
        _files_cache = sorted(n for n in names if os.path.lexists(ROOT / n))
    return _files_cache


def suffix_of(path: str) -> str:
    return Path(path).suffix.lower()


def is_scannable(path: str) -> bool:
    return suffix_of(path) in TEXT_EXT


def read_raw(rep: Report, path: str):
    """Return the file's bytes, or None (reported) when it cannot be read."""
    try:
        return (ROOT / path).read_bytes()
    except OSError:
        rep.error(path, 1, "FILE_UNREADABLE", "the file cannot be read (broken link or directory?)")
        return None


def text_of(rep: Report, path: str) -> str:
    if path not in _text_cache:
        raw = read_raw(rep, path)
        if raw is None:
            _text_cache[path] = ""
        else:
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("utf-8", "replace")
                rep.error(path, 1, "TEXT_ENCODING", "file must be valid UTF-8")
            _text_cache[path] = text.replace("\r\n", "\n")
    return _text_cache[path]


def line_of(text: str, needle: str) -> int:
    index = text.find(needle)
    return text.count("\n", 0, index) + 1 if index >= 0 else 1


def _no_duplicate_keys(pairs):
    seen = set()
    for key, _ in pairs:
        if key in seen:
            raise ValueError("duplicate key")
        seen.add(key)
    return dict(pairs)


def load_json(rep: Report, path: str):
    """Parse a JSON file once; report parse problems; return None when unusable."""
    if path in _json_cache:
        return _json_cache[path]
    data = None
    if path not in repo_files():
        rep.error(path, 1, "FILE_MISSING", "required file is missing")
    else:
        raw = read_raw(rep, path)
        if raw is not None:
            try:
                data = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_no_duplicate_keys)
            except json.JSONDecodeError as exc:
                rep.error(path, exc.lineno, "JSON_PARSE", "invalid JSON (see python3 -m json.tool)")
            except ValueError:
                rep.error(path, 1, "JSON_PARSE", "invalid JSON (see python3 -m json.tool)")
    _json_cache[path] = data
    return data


def dig(data, *keys):
    for key in keys:
        if not isinstance(data, dict) or key not in data:
            return None
        data = data[key]
    return data


def nonempty(value) -> bool:
    return isinstance(value, str) and value.strip() != ""


def semver_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


# ---------------------------------------------------------------------------
# Markdown helpers
# ---------------------------------------------------------------------------
def scan_fences(text: str):
    """Return (blocks, fenced_line_numbers, unclosed_start_line).

    blocks = [(info_string, content, first_line)]; line numbers are 1-based.
    """
    blocks: list[tuple[str, str, int]] = []
    fenced: set[int] = set()
    cur = None
    for number, line in enumerate(text.split("\n"), 1):
        if cur is None:
            match = FENCE_OPEN_RE.match(line)
            if match and not (match.group(1)[0] == "`" and "`" in match.group(2)):
                cur = {
                    "char": match.group(1)[0],
                    "size": len(match.group(1)),
                    "info": match.group(2).strip(),
                    "start": number,
                    "body": [],
                }
                fenced.add(number)
            continue
        fenced.add(number)
        match = FENCE_CLOSE_RE.match(line)
        if match and match.group(1)[0] == cur["char"] and len(match.group(1)) >= cur["size"]:
            blocks.append((cur["info"], "\n".join(cur["body"]), cur["start"]))
            cur = None
        else:
            cur["body"].append(line)
    unclosed = 0
    if cur is not None:
        unclosed = cur["start"]
        blocks.append((cur["info"], "\n".join(cur["body"]), cur["start"]))
    return blocks, fenced, unclosed


def blank_inline_code(line: str) -> str:
    return INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), line)


def extract_links(text: str) -> list[tuple[int, str]]:
    """(line, target) for Markdown links, HTML href/src/srcset and reference definitions."""
    _, fenced, _ = scan_fences(text)
    found: list[tuple[int, str]] = []
    for number, raw in enumerate(text.split("\n"), 1):
        if number in fenced:
            continue
        line = blank_inline_code(raw)
        for match in MD_LINK_RE.finditer(line):
            found.append((number, match.group(1)))
        for match in HTML_ATTR_RE.finditer(line):
            attr = match.group(1).lower()
            value = match.group(2) if match.group(2) is not None else match.group(3)
            if attr == "srcset":
                for candidate in value.split(","):
                    pieces = candidate.strip().split()
                    if pieces:
                        found.append((number, pieces[0]))
            else:
                found.append((number, value.strip()))
        match = REF_DEF_RE.match(line)
        if match:
            found.append((number, match.group(1)))
    return found


def headings_of(text: str) -> list[tuple[int, int, str]]:
    """(line, level, heading text) outside fenced code."""
    _, fenced, _ = scan_fences(text)
    result = []
    for number, line in enumerate(text.split("\n"), 1):
        if number in fenced:
            continue
        match = HEADING_RE.match(line)
        if match:
            result.append((number, len(match.group(1)), match.group(2)))
    return result


def github_slugs(text: str) -> set[str]:
    slugs: set[str] = set()
    used: Counter = Counter()
    for _, _, heading in headings_of(text):
        plain = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", heading)
        plain = re.sub(r"<[^>]+>", "", plain)
        plain = re.sub(r"[`*~]", "", plain).strip().lower()
        slug = re.sub(r"[^\w\- ]", "", plain).replace(" ", "-")
        count = used[slug]
        used[slug] += 1
        slugs.add(slug if count == 0 else f"{slug}-{count}")
    for match in re.finditer(r"""\b(?:id|name)\s*=\s*["']([^"']+)["']""", text):
        slugs.add(match.group(1).lower())
    return slugs


# ---------------------------------------------------------------------------
# (1) json
# ---------------------------------------------------------------------------
def check_json(rep: Report) -> None:
    files = repo_files()
    paths = sorted(set(MANIFESTS + [MCP_JSON] + [f for f in files if suffix_of(f) == ".json"]))
    for path in paths:
        if path not in files:
            rep.error(path, 1, "FILE_MISSING", "required file is missing")
            continue
        raw = read_raw(rep, path)
        if raw is None:
            continue
        if raw.startswith(b"\xef\xbb\xbf"):
            rep.error(path, 1, "JSON_BOM", "remove the UTF-8 byte order mark")
        tail = raw[len(raw.rstrip(b"\r\n")):]
        if tail not in (b"\n", b"\r\n"):
            rep.error(path, raw.count(b"\n") + 1, "JSON_EOF_NEWLINE", "end the file with exactly one newline")
        load_json(rep, path)


# ---------------------------------------------------------------------------
# (2) manifests
# ---------------------------------------------------------------------------
def marketplace_entry(rep: Report, market):
    if not isinstance(market, dict):
        return None
    plugins = market.get("plugins")
    if isinstance(plugins, list) and len(plugins) == 1 and isinstance(plugins[0], dict):
        return plugins[0]
    rep.error(P_MARKET, 1, "MARKETPLACE_PLUGINS", "marketplace.json must list exactly one plugin entry")
    return None


def manifest_objects(rep: Report) -> dict:
    """{path: the object that carries `version`}; None when the file is unusable (already reported)."""
    return {
        P_CLAUDE: load_json(rep, P_CLAUDE),
        P_MARKET: marketplace_entry(rep, load_json(rep, P_MARKET)),
        P_CODEX: load_json(rep, P_CODEX),
    }


def check_versions(rep: Report) -> str | None:
    """Validate the three versions; return the shared version (plugin.json) or None."""
    objects = manifest_objects(rep)
    reference = None
    for path, obj in objects.items():
        if not isinstance(obj, dict):
            continue
        version = obj.get("version")
        text = text_of(rep, path)
        if not (isinstance(version, str) and SEMVER_RE.match(version)):
            rep.error(path, line_of(text, '"version"'), "VERSION_FORMAT", "version must look like MAJOR.MINOR.PATCH")
            continue
        if reference is None:
            reference = version
        elif version != reference:
            rep.error(path, line_of(text, '"version"'), "VERSION_MISMATCH", "bump all three manifests together")
    return reference


def check_manifests(rep: Report) -> None:
    claude = load_json(rep, P_CLAUDE)
    market = load_json(rep, P_MARKET)
    codex = load_json(rep, P_CODEX)
    entry = marketplace_entry(rep, market)
    files = set(repo_files())

    def at(path: str, needle: str) -> int:
        return line_of(text_of(rep, path), needle) if path in files else 1

    check_versions(rep)

    # (b) identity
    for path, obj in ((P_CLAUDE, claude), (P_MARKET, market), (P_MARKET, entry), (P_CODEX, codex)):
        if isinstance(obj, dict) and obj.get("name") != "creagen":
            rep.error(path, at(path, '"name"'), "MANIFEST_NAME", 'name must be "creagen"')
    if entry is not None:
        if entry.get("source") != "./":
            rep.error(P_MARKET, at(P_MARKET, '"source"'), "MARKETPLACE_SOURCE", 'plugin source must be "./"')
        if claude is not None and entry.get("license") != claude.get("license"):
            rep.error(P_MARKET, at(P_MARKET, '"license"'), "MARKETPLACE_FIELD", "license must equal plugin.json")
        if claude is not None and entry.get("homepage") != claude.get("homepage"):
            rep.error(P_MARKET, at(P_MARKET, '"homepage"'), "MARKETPLACE_FIELD", "homepage must equal plugin.json")

    # (c) Claude plugin.json
    if isinstance(claude, dict):
        for key in ("name", "version", "description", "homepage", "repository", "privacyPolicyUrl",
                    "termsOfServiceUrl", "supportUrl", "documentationUrl"):
            if not nonempty(claude.get(key)):
                rep.error(P_CLAUDE, 1, "MANIFEST_FIELD", f"{key} is required")
        for key in ("author.name", "author.url"):
            if not nonempty(dig(claude, *key.split("."))):
                rep.error(P_CLAUDE, at(P_CLAUDE, '"author"'), "MANIFEST_FIELD", f"{key} is required")
        if claude.get("license") != "MIT":
            rep.error(P_CLAUDE, at(P_CLAUDE, '"license"'), "MANIFEST_FIELD", 'license must be "MIT"')
        keywords = claude.get("keywords")
        if not (isinstance(keywords, list) and keywords and all(nonempty(k) for k in keywords)):
            rep.error(P_CLAUDE, at(P_CLAUDE, '"keywords"'), "MANIFEST_FIELD", "keywords must be a non-empty list of strings")
        for key in ("homepage", "repository", "privacyPolicyUrl", "termsOfServiceUrl", "supportUrl",
                    "documentationUrl"):
            value = claude.get(key)
            if nonempty(value) and not value.startswith("https://"):
                rep.error(P_CLAUDE, at(P_CLAUDE, f'"{key}"'), "MANIFEST_URL", f"{key} must be an https URL")
        author_url = dig(claude, "author", "url")
        if nonempty(author_url) and not author_url.startswith("https://"):
            rep.error(P_CLAUDE, at(P_CLAUDE, '"author"'), "MANIFEST_URL", "author.url must be an https URL")

    # no hooks or inline servers in the manifests: the connector lives in .mcp.json
    for path, obj, keys in (
        (P_CLAUDE, claude, ("hooks", "mcpServers", "lspServers")),
        (P_MARKET, entry, ("hooks", "mcpServers", "lspServers")),
        (P_CODEX, codex, ("hooks", "lspServers")),
    ):
        for key in keys:
            if isinstance(obj, dict) and key in obj:
                rep.error(path, at(path, f'"{key}"'), "MANIFEST_EXECUTABLE",
                          "manifests must not declare hooks or servers (the connector lives in .mcp.json)")

    # (d) Codex plugin.json
    if isinstance(codex, dict):
        check_codex_manifest(rep, codex, files, at)

    # (e) parity between the Claude and Codex manifests
    if isinstance(claude, dict) and isinstance(codex, dict):
        pairs = (
            ("name", ("name",), ("name",)),
            ("version", ("version",), ("version",)),
            ("license", ("license",), ("license",)),
            ("author.name", ("author", "name"), ("author", "name")),
            ("author.url", ("author", "url"), ("author", "url")),
            ("homepage", ("homepage",), ("homepage",)),
            ("repository", ("repository",), ("repository",)),
            ("privacyPolicyUrl", ("privacyPolicyUrl",), ("interface", "privacyPolicyURL")),
            ("termsOfServiceUrl", ("termsOfServiceUrl",), ("interface", "termsOfServiceURL")),
            ("homepage/websiteURL", ("homepage",), ("interface", "websiteURL")),
        )
        for field, left, right in pairs:
            if dig(claude, *left) != dig(codex, *right):
                rep.error(P_CODEX, at(P_CODEX, f'"{right[-1]}"'), "PARITY",
                          f"{field} differs between {P_CLAUDE} and {P_CODEX}")

    # (f) connector definition
    check_mcp_json(rep)

    # (g) license text
    if "LICENSE" not in files:
        rep.error("LICENSE", 1, "FILE_MISSING", "required file is missing")
    else:
        first = text_of(rep, "LICENSE").split("\n", 1)[0]
        if "MIT License" not in first:
            rep.error("LICENSE", 1, "LICENSE_TEXT", "the first line must name the MIT License")


def check_codex_manifest(rep: Report, codex: dict, files: set, at) -> None:
    for key in ("name", "version", "description", "license", "skills", "mcpServers"):
        if not nonempty(codex.get(key)):
            rep.error(P_CODEX, 1, "MANIFEST_FIELD", f"{key} is required")
    if not nonempty(dig(codex, "author", "name")):
        rep.error(P_CODEX, at(P_CODEX, '"author"'), "MANIFEST_FIELD", "author.name is required")
    interface = codex.get("interface")
    if not isinstance(interface, dict):
        rep.error(P_CODEX, 1, "MANIFEST_FIELD", "interface is required")
        return
    for key in ("displayName", "shortDescription", "longDescription", "developerName", "websiteURL",
                "privacyPolicyURL", "termsOfServiceURL", "category", "composerIcon", "logo"):
        if not nonempty(interface.get(key)):
            rep.error(P_CODEX, at(P_CODEX, '"interface"'), "MANIFEST_FIELD", f"interface.{key} is required")
    capabilities = interface.get("capabilities")
    if not (isinstance(capabilities, list) and capabilities and set(capabilities) <= {"Read", "Write"}):
        rep.error(P_CODEX, at(P_CODEX, '"capabilities"'), "MANIFEST_FIELD",
                  "interface.capabilities must be a non-empty list drawn from Read and Write")
    prompts = interface.get("defaultPrompt")
    if not (isinstance(prompts, list) and 1 <= len(prompts) <= 3 and all(nonempty(p) for p in prompts)):
        rep.error(P_CODEX, at(P_CODEX, '"defaultPrompt"'), "MANIFEST_FIELD",
                  "interface.defaultPrompt must hold one to three strings")

    def rel_path(value):
        if not (isinstance(value, str) and value.startswith("./")) or ".." in value.split("/"):
            return None
        return posixpath.normpath(value[2:] or ".")

    skills = rel_path(codex.get("skills"))
    if skills is None:
        rep.error(P_CODEX, at(P_CODEX, '"skills"'), "MANIFEST_PATH", "paths must be relative and start with ./")
    elif not any(f.startswith(skills + "/") for f in files):
        rep.error(P_CODEX, at(P_CODEX, '"skills"'), "MANIFEST_PATH", "the skills directory does not exist")
    if codex.get("mcpServers") != "./.mcp.json":
        rep.error(P_CODEX, at(P_CODEX, '"mcpServers"'), "MANIFEST_PATH", "mcpServers must be ./.mcp.json")
    elif MCP_JSON not in files:
        rep.error(P_CODEX, at(P_CODEX, '"mcpServers"'), "MANIFEST_PATH", "the referenced connector file does not exist")
    for key in ("composerIcon", "logo"):
        value = interface.get(key)
        rel = rel_path(value)
        if rel is None or not re.match(r"^assets/[^/]+\.png$", rel):
            rep.error(P_CODEX, at(P_CODEX, f'"{key}"'), "MANIFEST_PATH", f"{key} must be ./assets/<name>.png")
        elif rel not in files:
            rep.error(P_CODEX, at(P_CODEX, f'"{key}"'), "MANIFEST_PATH", f"{key} file does not exist")


def check_mcp_json(rep: Report) -> None:
    data = load_json(rep, MCP_JSON)
    if data is None:
        return
    text = text_of(rep, MCP_JSON)
    servers = dig(data, "mcpServers")
    if not (isinstance(servers, dict) and list(servers) == ["creagen"]):
        rep.error(MCP_JSON, line_of(text, '"mcpServers"'), "MCP_SHAPE",
                  "declare exactly one server named creagen")
        return
    server = servers["creagen"]
    if not isinstance(server, dict) or server.get("type") != "http":
        rep.error(MCP_JSON, line_of(text, '"type"'), "MCP_SHAPE", 'the creagen server must have type "http"')
    if isinstance(server, dict) and set(server) != {"type", "url"}:
        rep.error(MCP_JSON, line_of(text, '"creagen"'), "MCP_SHAPE",
                  "the creagen server may define only type and url (no command, env or headers)")
    url = server.get("url") if isinstance(server, dict) else None
    ok = False
    if isinstance(url, str):
        try:
            parts = urlsplit(url)
            ok = parts.scheme == "https" and parts.hostname == MCP_HOST and parts.port is None
        except ValueError:
            ok = False
    if not ok:
        rep.error(MCP_JSON, line_of(text, '"url"'), "MCP_URL", "connector must be https on the public Creagen host")


# ---------------------------------------------------------------------------
# (3) skills
# ---------------------------------------------------------------------------
def parse_front_matter(rep: Report, path: str, lines: list[str]):
    """Return (fields, closing_index) or None. fields = {key: (value, line)}."""
    if not lines or lines[0] != "---":
        rep.error(path, 1, "SKILL_FM_SYNTAX", "the file must start with a --- front matter block")
        return None
    fields: dict[str, tuple[str, int]] = {}
    for index in range(1, len(lines)):
        line = lines[index]
        if line == "---":
            return fields, index
        match = FM_LINE_RE.match(line)
        if not match:
            rep.error(path, index + 1, "SKILL_FM_SYNTAX", "front matter allows only single-line key: value pairs")
            continue
        key, value = match.group(1), match.group(2).rstrip()
        if key in fields:
            rep.error(path, index + 1, "SKILL_FM_SYNTAX", "duplicate front matter key")
            continue
        fields[key] = (value, index + 1)
    rep.error(path, 1, "SKILL_FM_SYNTAX", "front matter block is not closed with ---")
    return None


def check_skills(rep: Report) -> None:
    files = repo_files()
    skill_files: dict[str, list[list[str]]] = {}
    for path in files:
        if not path.startswith("skills/"):
            continue
        parts = path.split("/")
        if len(parts) == 2:
            rep.error(path, 1, "SKILLS_LAYOUT", "skills/ may contain only skill directories")
            continue
        skill_files.setdefault(parts[1], []).append(parts[2:])
    for name in sorted(skill_files):
        rels = skill_files[name]
        for rel in rels:
            if rel != ["SKILL.md"]:
                rep.error("skills/" + name + "/" + "/".join(rel), 1, "SKILL_EXTRA_FILE",
                          "a skill directory may contain only SKILL.md")
        if ["SKILL.md"] not in rels:
            rep.error("skills/" + name, 1, "SKILL_MISSING", "add skills/<name>/SKILL.md")
            continue
        check_skill_file(rep, name)
    if CREDIT_GUARD_SKILL not in skill_files:
        rep.error("skills/" + CREDIT_GUARD_SKILL + "/SKILL.md", 1, "SKILL_CREDIT_GUARD",
                  "the credit-quote and completion-check wording must stay in creagen-generate")

    # README mentions and badge count
    for readme in READMES:
        if readme not in files:
            continue
        text = text_of(rep, readme)
        for name in sorted(skill_files):
            if f"`{name}`" not in text:
                rep.error(readme, 1, "SKILL_README_MENTION", "add the skill to all three READMEs")
        badges = re.findall(r"img\.shields\.io/badge/skills-(\d+)-", text)
        if not badges:
            rep.error(readme, 1, "SKILL_BADGE_COUNT", "the skills badge is missing")
        for number in badges:
            if int(number) != len(skill_files):
                rep.error(readme, line_of(text, "badge/skills-"), "SKILL_BADGE_COUNT",
                          "the skills badge must show the number of skill directories")


def check_skill_file(rep: Report, name: str) -> None:
    path = f"skills/{name}/SKILL.md"
    text = text_of(rep, path)
    lines = text.split("\n")
    parsed = parse_front_matter(rep, path, lines)
    if parsed is None:
        return
    fields, closing = parsed
    if set(fields) != {"name", "description", "license"}:
        rep.error(path, 1, "SKILL_FM_KEYS",
                  "only name, description, license are allowed (no version key; versions live in the manifests)")
    if "name" in fields:
        value, line = fields["name"]
        if value != name or not SKILL_NAME_RE.match(value):
            rep.error(path, line, "SKILL_NAME", "name must equal the directory name and look like creagen-<words>")
    if "description" in fields:
        value, line = fields["description"]
        if len(value) < 2 or value[0] != '"' or value[-1] != '"':
            rep.error(path, line, "SKILL_DESC", "description must be one double-quoted line")
        else:
            inner = value[1:-1]
            if re.search(r'(?<!\\)"', inner):
                rep.error(path, line, "SKILL_DESC", "escape double quotes inside the description")
            elif not 20 <= len(inner) <= 1024:
                rep.error(path, line, "SKILL_DESC", "description must be 20 to 1024 characters")
    if "license" in fields:
        value, line = fields["license"]
        if value not in ("MIT", '"MIT"', "'MIT'"):
            rep.error(path, line, "SKILL_LICENSE", "license must be MIT")

    body = "\n".join(lines[closing + 1:])
    _, fenced, _ = scan_fences(text)
    h1_lines = [n for n, line in enumerate(lines, 1)
                if n > closing + 1 and n not in fenced and line.startswith("# ")]
    if len(h1_lines) != 1:
        rep.error(path, h1_lines[1] if len(h1_lines) > 1 else closing + 2, "SKILL_H1",
                  "exactly one H1 heading is required")
    if name == CREDIT_GUARD_SKILL:
        if not all(token in body for token in CREDIT_GUARD_TOKENS):
            rep.error(path, 1, "SKILL_CREDIT_GUARD",
                      "the credit-quote and completion-check wording must stay in creagen-generate")
    elif not re.search(r"credit", body, re.I):
        rep.warn(path, 1, "SKILL_CREDIT_MENTION", "this skill never mentions credits; confirm spending is covered")


# ---------------------------------------------------------------------------
# (4) readme
# ---------------------------------------------------------------------------
def is_switch_line(line: str) -> bool:
    return all(name in line for name in LANG_NAMES.values())


def readme_facts(text: str) -> dict:
    blocks, fenced, _ = scan_fences(text)
    code: Counter = Counter()
    mermaid: Counter = Counter()
    for info, body, _ in blocks:
        if info.lower().startswith("mermaid"):
            mermaid[re.sub(r'"[^"]*"', '""', body)] += 1
        else:
            code[(info, body)] += 1
    prose = "\n".join(line for line in text.split("\n") if not is_switch_line(line))
    relative = Counter(target for _, target in extract_links(prose)
                       if not re.match(r"^(?:https?:|mailto:|#)", target, re.I))
    lines = text.split("\n")
    return {
        "urls": Counter(url.rstrip(".,;:") for url in README_URL_RE.findall(text)),
        "relative": relative,
        "code": code,
        "mermaid": mermaid,
        "badges": set(re.findall(SHIELDS_IMG_RE, text)),
        "pictures": re.findall(r"<picture>.*?</picture>", text, re.S),
        "h2": sum(1 for n, line in enumerate(lines, 1) if n not in fenced and line.startswith("## ")),
    }


def check_readme(rep: Report) -> None:
    files = set(repo_files())
    missing = [r for r in READMES if r not in files]
    for readme in missing:
        rep.error(readme, 1, "FILE_MISSING", "required file is missing")
    if missing:
        return
    texts = {r: text_of(rep, r) for r in READMES}
    facts = {r: readme_facts(texts[r]) for r in READMES}
    canonical = facts["README.md"]
    for readme in READMES[1:]:
        current = facts[readme]
        if current["urls"] != canonical["urls"]:
            rep.error(readme, 1, "README_URLS", "link set differs from README.md")
        if current["relative"] != canonical["relative"]:
            rep.error(readme, 1, "README_RELLINKS", "relative links and images differ from README.md")
        if current["code"] != canonical["code"] or current["mermaid"] != canonical["mermaid"]:
            rep.error(readme, 1, "README_CODEBLOCKS",
                      "code blocks must match README.md (a diagram may translate its labels only)")
        if current["badges"] != canonical["badges"]:
            rep.error(readme, 1, "README_BADGES", "badge set differs from README.md")
        if current["pictures"] != canonical["pictures"]:
            rep.error(readme, 1, "README_PICTURE", "the <picture> block differs from README.md")
        if current["h2"] != canonical["h2"]:
            rep.warn(readme, 1, "README_H2_COUNT", "the number of ## sections differs from README.md")
    for readme in READMES:
        text = texts[readme]
        for match in BADGE_LOGO_RE.finditer(text):
            rep.error(readme, text.count("\n", 0, match.start()) + 1, "README_BADGE_LOGO",
                      "third-party brand logos are not allowed in badges; text badges only")
        check_lang_switch(rep, readme, text)
    base = os.environ.get("BASE_REF", "").strip()
    if base:
        changes = base_changes(rep, base, "README.md", "README_BASE_UNAVAILABLE")
        if changes is not None:
            touched = {p for p in changes[1] if p in READMES}
            if len(touched) not in (0, len(READMES)):
                for readme in READMES:
                    if readme not in touched:
                        rep.error(readme, 1, "README_PARTIAL_UPDATE",
                                  "update README.md, README.ko.md and README.ja.md together")


def check_lang_switch(rep: Report, readme: str, text: str) -> None:
    candidates = [(n, line) for n, line in enumerate(text.split("\n"), 1) if is_switch_line(line)]
    message = "keep one language switcher line that links the other two READMEs and bolds this one"
    if len(candidates) != 1:
        rep.error(readme, candidates[1][0] if len(candidates) > 1 else 1, "README_LANG_SWITCH", message)
        return
    number, line = candidates[0]
    hrefs = re.findall(r'<a href="(README(?:\.ko|\.ja)?\.md)">', line)
    bold = re.findall(r"<b>(.*?)</b>", line)
    others = sorted(r for r in READMES if r != readme)
    if sorted(hrefs) != others or bold != [LANG_NAMES[readme]]:
        rep.error(readme, number, "README_LANG_SWITCH", message)


def base_changes(rep: Report, base: str, path: str, rule: str):
    """Return (merge_base, changed_paths) comparing the working tree with the merge base."""
    try:
        merge_base = git("merge-base", base, "HEAD").strip()
        changed = {p for p in git("diff", "--name-only", "--no-renames", "-z", merge_base).split("\0") if p}
        changed |= {p for p in git("ls-files", "-z", "--others", "--exclude-standard").split("\0") if p}
    except GitError:
        rep.error(path, 1, rule, "run git fetch origin <base> (CI uses fetch-depth 0)")
        return None
    return merge_base, changed


# ---------------------------------------------------------------------------
# (5) links
# ---------------------------------------------------------------------------
def check_links(rep: Report) -> None:
    files = repo_files()
    known = set(files)
    slug_cache: dict[str, set[str]] = {}

    def slugs_for(path: str) -> set[str]:
        if path not in slug_cache:
            slug_cache[path] = github_slugs(text_of(rep, path))
        return slug_cache[path]

    for path in files:
        if suffix_of(path) != ".md":
            continue
        text = text_of(rep, path)
        unclosed = scan_fences(text)[2]
        if unclosed:
            rep.error(path, unclosed, "MD_FENCE_UNCLOSED", "close the code fence")
        for line, target in extract_links(text):
            check_one_link(rep, path, line, target, known, slugs_for)


def check_one_link(rep: Report, path: str, line: int, target: str, known: set, slugs_for) -> None:
    if not target:
        rep.error(path, line, "LINK_BROKEN", "target not found (case-sensitive)")
        return
    lowered = target.lower()
    if lowered.startswith(("http://", "https://")):
        try:
            host = urlsplit(target).hostname
        except ValueError:
            host = None
        if not host:
            rep.error(path, line, "LINK_URL", "malformed URL")
        return
    if lowered.startswith("mailto:"):
        address = unquote(target[7:]).split("?", 1)[0].strip().lower()
        if address not in ALLOWED_EMAILS:
            rep.error(path, line, "LINK_MAILTO", "only the support address may be linked with mailto:")
        return
    if SCHEME_RE.match(target):
        rep.error(path, line, "LINK_SCHEME", "only https, mailto, relative and #anchor links are allowed")
        return
    file_part, _, anchor = target.partition("#")
    file_part = file_part.split("?", 1)[0]
    if file_part:
        file_part = unquote(file_part)
        joined = file_part.lstrip("/") if file_part.startswith("/") else posixpath.join(posixpath.dirname(path), file_part)
        resolved = posixpath.normpath(joined)
        if resolved == ".." or resolved.startswith("../"):
            rep.error(path, line, "LINK_BROKEN", "target not found (case-sensitive)")
            return
        exists = resolved in known or any(f.startswith(resolved + "/") for f in known)
        if not exists:
            rep.error(path, line, "LINK_BROKEN", "target not found (case-sensitive)")
            return
    else:
        resolved = path
    if anchor and resolved.endswith(".md") and resolved in known:
        if unquote(anchor).lower() not in slugs_for(resolved):
            rep.error(path, line, "LINK_ANCHOR", "anchor not found in the target file")


# ---------------------------------------------------------------------------
# (6) leaks
# ---------------------------------------------------------------------------
def in_wording_scope(path: str) -> bool:
    return (path.startswith("skills/") and path.endswith("/SKILL.md")) or path in READMES or path in MANIFESTS


def in_prose_scope(kind: str, path: str) -> bool:
    """Text that people write and read: Markdown, JSON, issue forms and every commit or pull-request text.
    Workflows and scripts are not prose, so dotted code names there are never read as hosts."""
    return kind != "file" or suffix_of(path) in (".md", ".json") or path.startswith(".github/ISSUE_TEMPLATE/")


def url_problem(url: str, kind: str):
    """Return the rule name when the URL is not acceptable, else None."""
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        port = parts.port
    except ValueError:
        return "LEAK_HOST"
    if not host:
        return None
    if host in LOCAL_HOSTS or port is not None:
        return "LEAK_LOCAL_URL"
    if host == "github.com":
        path = parts.path or "/"
        if any(path == p or path.startswith(p + "/") for p in ALLOWED_GITHUB_PREFIXES):
            return None
        return "LEAK_HOST"
    if host in ALLOWED_HOSTS or (kind != "file" and host in MESSAGE_ONLY_HOSTS):
        return None
    return "LEAK_HOST"


def blank(match) -> str:
    return " " * len(match.group(0))


def repo_link(url: str) -> bool:
    """True for a link into this repository: the numbers in its issue, pull request and run URLs are public."""
    try:
        return (urlsplit(url).hostname or "").lower() == "github.com" and url_problem(url, "file") is None
    except ValueError:
        return False


def mask_repo_links(line: str) -> str:
    return URL_RE.sub(lambda m: blank(m) if repo_link(m.group(0).rstrip(".,;:!?*_~")) else m.group(0), line)


def has_bare_host_problem(line: str, kind: str) -> bool:
    """True when the line names a host without https:// (a dashboard, a chat workspace) that is not allowed.
    Links and email addresses are blanked first: they have their own rules."""
    plain = EMAIL_RE.sub(blank, URL_RE.sub(blank, line))
    for match in BARE_HOST_RE.finditer(plain):
        host = match.group(1).lower()
        rest = (match.group(2) or "").rstrip(".,;:!?*_~")
        if host.rsplit(".", 1)[1] not in BARE_HOST_TLDS or host in TEXT_ONLY_HOSTS:
            continue
        if host == "github.com" and not rest:
            continue  # naming the site is not a link to a repository
        if url_problem("https://" + host + rest, kind) is not None:
            return True
    return False


def scan_source(rep: Report, kind: str, label: str, text: str, path: str = "", full: bool = True,
                lenient: bool = False) -> None:
    """Scan one text source. kind is file | message. `full` False skips the rules that
    would match this script's own pattern constants. `lenient` is for bot-written message text
    that quotes upstream release notes: host and long-number findings stay warnings there."""
    allowed_emails = set(ALLOWED_EMAILS)
    if kind != "file" or not full:  # this script defines the message-only addresses itself
        allowed_emails |= MESSAGE_ONLY_EMAILS
    host_report = rep.warn if lenient else rep.error
    id_report = host_report
    prose = in_prose_scope(kind, path)
    for number, line in enumerate(text.split("\n"), 1):
        for match in URL_RE.finditer(line):
            rule = url_problem(match.group(0).rstrip(".,;:!?*_~"), kind)
            if rule == "LEAK_LOCAL_URL":
                rep.error(label, number, rule, "URLs must not point at local hosts or explicit ports")
            elif rule == "LEAK_HOST":
                host_report(label, number, rule,
                            "URL host is not in ALLOWED_HOSTS: remove the link, or add the public host "
                            "at the top of check.py and explain why in the PR")
        for match in EMAIL_RE.finditer(line):
            address = match.group(0).lower()
            if address in allowed_emails or (kind != "file" and NOREPLY_RE.search(address)):
                continue
            rep.error(label, number, "LEAK_EMAIL", "email addresses are not allowed except the support address")
        folded = unicodedata.normalize("NFKC", INVISIBLE_RE.sub("", line))
        if any(pattern.search(line) or pattern.search(folded) for pattern in SECRET_RES):
            rep.error(label, number, "LEAK_SECRET", "remove the credential-like string and rotate it if it was real")
        if not full:
            continue
        if LOCAL_WORD_RE.search(line):
            rep.error(label, number, "LEAK_LOCAL_URL", "URLs must not point at local hosts or explicit ports")
        if NUM_ID_RE.search(mask_repo_links(line)):
            id_report(label, number, "LEAK_NUMERIC_ID", "6+ digit identifiers are not allowed")
        if prose and has_bare_host_problem(line, kind):
            host_report(label, number, "LEAK_BARE_HOST",
                        "a hostname written without https:// is not in ALLOWED_HOSTS: remove it, or add the "
                        "public host at the top of check.py and explain why in the PR")
        if not (kind == "file" and path in READMES) and BADGE_LOGO_RE.search(line):
            rep.error(label, number, "BADGE_LOGO", "third-party brand logos are not allowed in badges; text badges only")
    if kind == "file" and full and in_wording_scope(path):
        flat = text.replace("\n", " ")
        for pattern in INJECTION_RES:
            for match in pattern.finditer(flat):
                rep.error(label, text.count("\n", 0, match.start()) + 1, "INJECTION",
                          "instruction wording that steers tool use or pulls outside instructions is not allowed")
        for pattern in PROMO_RES:
            for match in pattern.finditer(flat):
                rep.error(label, text.count("\n", 0, match.start()) + 1, "PROMO",
                          "promotional or comparative claims are not allowed")


def commit_messages(rep: Report, git_range: str):
    two_dot = git_range.replace("...", "..")
    try:
        out = git("log", "--format=%H%x1f%B%x1e", two_dot)
    except GitError:
        rep.error("git-log", 1, "LEAK_RANGE_UNAVAILABLE", "run git fetch origin <base> (CI uses fetch-depth 0)")
        return []
    messages = []
    for record in out.split("\x1e"):
        record = record.strip("\n")
        if not record:
            continue
        sha, _, body = record.partition("\x1f")
        messages.append((f"commit-{sha.strip()[:7]}", body))
    return messages


def check_leaks(rep: Report, git_range: str = "") -> None:
    for path in repo_files():
        if not is_scannable(path):
            continue
        text = text_of(rep, path)
        scan_source(rep, "file", path, text, path=path, full=(path != SELF))
    # Commit messages and the pull request text are public and permanent like files, so hosts and
    # long numbers are errors there too. Only text a bot copies from upstream release notes is lenient.
    lenient = os.environ.get("PR_AUTHOR", "").strip().lower() in BOT_AUTHORS
    if git_range:
        for label, body in commit_messages(rep, git_range):
            scan_source(rep, "message", label, body, lenient=lenient)
    for label, variable in (("pr-title", "PR_TITLE"), ("pr-body", "PR_BODY")):
        value = os.environ.get(variable, "")
        if value.strip():
            scan_source(rep, "message", label, value.replace("\r\n", "\n"), lenient=lenient)


# ---------------------------------------------------------------------------
# (7) changelog
# ---------------------------------------------------------------------------
def check_changelog(rep: Report) -> None:
    path = "CHANGELOG.md"
    files = set(repo_files())
    manifest_version = dig(load_json(rep, P_CLAUDE), "version")
    if path not in files:
        rep.error(path, 1, "CHANGELOG_MISSING", "add CHANGELOG.md")
        return
    text = text_of(rep, path)
    _, fenced, _ = scan_fences(text)
    headings = [(n, line) for n, line in enumerate(text.split("\n"), 1)
                if n not in fenced and line.startswith("## ")]
    if not headings or headings[0][1] != "## [Unreleased]":
        rep.error(path, headings[0][0] if headings else 1, "CHANGELOG_UNRELEASED",
                  "keep an [Unreleased] section at the top")
    releases = []
    for number, line in headings[1:]:
        match = CL_RELEASE_RE.match(line)
        valid_date = False
        if match:
            try:
                datetime.date.fromisoformat(match.group(2))
                valid_date = True
            except ValueError:
                valid_date = False
        if not (match and valid_date):
            rep.error(path, number, "CHANGELOG_FORMAT", "release headings look like ## [x.y.z] - YYYY-MM-DD")
        else:
            releases.append((number, match.group(1)))
    if not releases:
        rep.error(path, 1, "CHANGELOG_VERSION", "top release heading must equal the manifest version")
    elif isinstance(manifest_version, str) and releases[0][1] != manifest_version:
        rep.error(path, releases[0][0], "CHANGELOG_VERSION", "top release heading must equal the manifest version")

    event = os.environ.get("EVENT", "").strip()
    base = os.environ.get("BASE_REF", "").strip()
    if event != "pull_request" or not base or not isinstance(manifest_version, str):
        return
    changes = base_changes(rep, base, path, "CHANGELOG_BASE_UNAVAILABLE")
    if changes is None:
        return
    merge_base, changed = changes
    try:
        base_manifest = json.loads(git("show", f"{merge_base}:{P_CLAUDE}"))
        base_version = base_manifest.get("version")
        if not (isinstance(base_version, str) and SEMVER_RE.match(base_version)):
            raise GitError("bad base version")
    except (GitError, ValueError, AttributeError):
        rep.error(path, 1, "CHANGELOG_BASE_UNAVAILABLE", "run git fetch origin <base> (CI uses fetch-depth 0)")
        return
    if not SEMVER_RE.match(manifest_version):
        return
    if manifest_version != base_version:
        if semver_tuple(manifest_version) < semver_tuple(base_version):
            rep.error(P_CLAUDE, line_of(text_of(rep, P_CLAUDE), '"version"'), "VERSION_DOWNGRADE",
                      "the version must not go backwards")
            return
        try:
            base_changelog = git("show", f"{merge_base}:{path}")
        except GitError:
            base_changelog = ""
        heading = re.compile(r"^## \[" + re.escape(manifest_version) + r"\] - ", re.M)
        if len(heading.findall(text)) <= len(heading.findall(base_changelog)):
            rep.error(path, 1, "CHANGELOG_ENTRY_MISSING",
                      "move the Unreleased notes under ## [<new>] - <date>")
    else:
        visible = [p for p in sorted(changed)
                   if p.startswith("skills/") or p in READMES or p in MANIFESTS or p == MCP_JSON]
        if visible:
            rep.warn(path, 1, "CHANGELOG_CONSIDER_BUMP",
                     "user-visible files changed without a version bump; fine for typos and clarifications")


# ---------------------------------------------------------------------------
# (8) tree
# ---------------------------------------------------------------------------
def check_tree(rep: Report) -> None:
    files = repo_files()
    for entry in sorted({f.split("/")[0] for f in files}):
        if entry == "CLAUDE.md":
            rep.error(entry, 1, "TREE_ROOT", "CLAUDE.md at the root fails the plugin validator; use .claude/CLAUDE.md")
        elif entry not in ROOT_ALLOWED:
            rep.error(entry, 1, "TREE_ROOT", "unexpected top-level entry")
    index_modes: dict[str, str] = {}
    try:
        for record in git("ls-files", "-s", "-z").split("\0"):
            if record:
                meta, _, name = record.partition("\t")
                index_modes[name] = meta.split()[0]
    except GitError:
        pass
    for path in files:
        suffix = suffix_of(path)
        full = ROOT / path
        if not path.startswith(".github/") and suffix in RUNNABLE_EXT:
            rep.error(path, 1, "TREE_RUNNABLE", "runnable files live only under .github/")
        if suffix not in TEXT_EXT and suffix not in BINARY_EXT:
            rep.error(path, 1, "TREE_FILETYPE", "only Markdown, JSON, YAML, PNG and the .github/ tooling are allowed")
        if os.path.islink(full) or index_modes.get(path) == "120000":
            rep.error(path, 1, "TREE_SYMLINK", "symbolic links are not allowed")
            continue
        try:
            mode = os.stat(full).st_mode
        except OSError:
            rep.error(path, 1, "FILE_UNREADABLE", "the file cannot be read (broken link or directory?)")
            continue
        if (index_modes.get(path) == "100755" or bool(mode & 0o111)) and not path.startswith(EXEC_ALLOWED_PREFIX):
            rep.error(path, 1, "TREE_EXEC_BIT", "only .github/scripts/ may hold executable files")
        if path.startswith("assets/"):
            head = read_raw(rep, path)
            if suffix != ".png":
                rep.error(path, 1, "TREE_ASSET", "assets/ holds PNG files only")
            elif head is not None and head[:8] != b"\x89PNG\r\n\x1a\n":
                rep.error(path, 1, "TREE_ASSET", "the file is not a valid PNG")
            elif head is not None and len(head) > ASSET_MAX_BYTES:
                rep.error(path, 1, "TREE_ASSET", "assets must be 200 KB or smaller")
        if path.startswith(".claude/") and path not in CLAUDE_DIR_ALLOWED:
            rep.error(path, 1, "TREE_CLAUDE_DIR", "only .claude/CLAUDE.md may live in .claude/ (settings and hooks are not allowed)")
        parts = path.split("/")
        if parts[0] == "skills" and len(parts) >= 3 and parts[2:] != ["SKILL.md"]:
            rep.error(path, 1, "TREE_SKILL_FILE", "a skill directory may contain only SKILL.md")


# ---------------------------------------------------------------------------
# (9) workflows
# ---------------------------------------------------------------------------
def strip_yaml_comment(line: str) -> str:
    """Drop a trailing `# comment` (a # outside quotes and after a space) and trailing spaces."""
    quote = ""
    for index, char in enumerate(line):
        if quote:
            if char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
        elif char == "#" and (index == 0 or line[index - 1] in " \t"):
            return line[:index].rstrip()
    return line.rstrip()


def key_block(lines: list[str], index: int, column: int) -> list[tuple[int, str]]:
    """(line number, text) of the lines nested under the key on lines[index]; blank lines are skipped."""
    block = []
    for follow in range(index + 1, len(lines)):
        text = lines[follow]
        if not text.strip():
            continue
        if len(text) - len(text.lstrip(" ")) <= column:
            break
        block.append((follow + 1, text))
    return block


def scan_workflow(rep: Report, path: str, raw: list[str]) -> None:
    lines = [strip_yaml_comment(line) for line in raw]
    has_top_level_permissions = False
    # Script bodies are shell, not YAML: a * or & there is not an alias, and only ${{ }} matters.
    script_body = set()
    for index, line in enumerate(lines):
        found = WORKFLOW_KEY_RE.match(line)
        # Only a block scalar (| or >) is a script body; a job id or mapping key that is
        # merely named run or script opens YAML, and must be scanned as YAML.
        if (found and found.group(2) in ("run", "script")
                and (found.group(3) or "").strip()[:1] in ("|", ">")):
            script_body.update(at - 1 for at, _ in key_block(raw, index, len(found.group(1))))
    for index, line in enumerate(lines):
        number = index + 1
        # A lone CR, NEL, LS or PS is a line break to a YAML parser but not to this scan,
        # so it could hide a second step inside a script body. Reject it everywhere.
        if any(char in raw[index] for char in ("\r", "\x85", "\u2028", "\u2029")):
            rep.error(path, number, "WORKFLOW_STYLE",
                      "use plain ASCII with spaces only (no tabs, carriage returns or look-alike characters) in workflow code")
        if index in script_body:
            if "${{" in raw[index]:
                rep.error(path, number, "WORKFLOW_RUN_EXPRESSION",
                          "pass values to a script through env:, never with ${{ }} inside run or script")
            if WORKFLOW_SECRETS_RE.search(raw[index]):
                rep.error(path, number, "WORKFLOW_SECRETS", "workflows must not read secrets; the CI needs none")
            continue
        # Normalise first so a look-alike spelling cannot slip past the rules below.
        ascii_only = not any(ord(char) > 126 for char in line)
        line = unicodedata.normalize("NFKC", INVISIBLE_RE.sub("", line))
        if not ascii_only or "\t" in line:
            rep.error(path, number, "WORKFLOW_STYLE",
                      "use plain ASCII with spaces only (no tabs, carriage returns or look-alike characters) in workflow code")
        if WORKFLOW_ESCAPE_RE.search(line):
            rep.error(path, number, "WORKFLOW_STYLE", "do not use backslash escapes in workflow YAML; check.py cannot read them")
        if WORKFLOW_INDIRECT_RE.search(line) and not line.lstrip().startswith("#"):
            rep.error(path, number, "WORKFLOW_STYLE",
                      "do not use anchors, aliases, tags, complex keys or merge keys; check.py reads plain block YAML only")
        if index > 0 and WORKFLOW_DOC_RE.match(line):
            rep.error(path, number, "WORKFLOW_STYLE", "one YAML document per workflow file")
        if WORKFLOW_TRIGGER_RE.search(line):
            rep.error(path, number, "WORKFLOW_TRIGGER",
                      "pull_request_target and workflow_run give an untrusted change the repository's trust; use pull_request")
        if WORKFLOW_SECRETS_RE.search(line):
            rep.error(path, number, "WORKFLOW_SECRETS", "workflows must not read secrets; the CI needs none")
        if WORKFLOW_FLOW_RE.search(line):
            rep.error(path, number, "WORKFLOW_STYLE", "write workflows as plain block YAML; check.py cannot read flow mappings")
        match = WORKFLOW_KEY_RE.match(line)
        if not match:
            continue
        prefix, key, value = match.group(1), match.group(2), (match.group(3) or "").strip()
        column = len(prefix)
        if key == "uses":
            action = value[1:-1] if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'" else value
            if not WORKFLOW_ACTION_RE.match(action):
                rep.error(path, number, "WORKFLOW_USES",
                          "use only actions/* actions pinned to a full 40-character commit SHA (put the version in a trailing comment)")
        elif key in ("run", "script"):
            if value.startswith("*"):
                rep.error(path, number, "WORKFLOW_STYLE", "write the script inline; check.py cannot read a YAML alias")
            # Raw lines, comments included: a script body is not YAML, so a # there is text.
            for at, text in [(number, raw[index])] + key_block(raw, index, column):
                if "${{" in text:
                    rep.error(path, at, "WORKFLOW_RUN_EXPRESSION",
                              "pass values to a script through env:, never with ${{ }} inside run or script")
        elif key == "permissions":
            top_level = prefix == ""
            has_top_level_permissions = has_top_level_permissions or top_level
            if value:
                rep.error(path, number, "WORKFLOW_PERMISSIONS",
                          "write permissions as a block; the top level allows only contents: read")
                continue
            items = []
            for at, text in key_block(lines, index, column):
                item = WORKFLOW_PERM_ITEM_RE.match(text)
                items.append((at, item.group(1), item.group(2)) if item else (at, None, None))
            for at, scope, level in items:
                if scope is None or level not in ("read", "none"):
                    rep.error(path, at, "WORKFLOW_PERMISSIONS", "grant read access only (no write, no write-all)")
            if top_level and [(scope, level) for _, scope, level in items] != [("contents", "read")]:
                rep.error(path, number, "WORKFLOW_PERMISSIONS", "the top-level permissions must be exactly contents: read")
    if not has_top_level_permissions:
        rep.error(path, 1, "WORKFLOW_PERMISSIONS", "declare top-level permissions with contents: read")


def check_workflows(rep: Report) -> None:
    for path in repo_files():
        if WORKFLOW_PATH_RE.match(path):
            scan_workflow(rep, path, text_of(rep, path).split("\n"))



# ---------------------------------------------------------------------------
# (11) selftest: the leak and workflow rules must keep rejecting known bypasses
# ---------------------------------------------------------------------------
def _scan_rules(kind: str, text: str, path: str = "") -> set:
    probe = Report()
    scan_source(probe, kind, "selftest", text, path=path)
    return {item[3] for item in probe.items if item[0] == "error"}


def _workflow_rules(text: str) -> set:
    probe = Report()
    scan_workflow(probe, ".github/workflows/selftest.yml", text.split("\n"))
    return {item[3] for item in probe.items if item[0] == "error"}


def check_selftest(rep: Report) -> None:
    """Each case is one bypass seen or plausible; it must be reported, and the clean case must not.
    Secret-shaped samples are assembled at run time so this file never contains one."""
    fill = "A1b2C3d4E5f6G7h8I9j0K1l2M3"
    zero_width = chr(0x200B)
    fullwidth_k = chr(0xFF4B)
    secret_cases = {
        "sk with hyphens": "key " + "sk-" + "proj-" + fill,
        "sk anthropic style": "sk-" + "ant-api03-" + fill,
        "stripe live": "sk_" + "live_" + fill,
        "gitlab pat": "glpat" + "-" + fill,
        "npm token": "npm" + "_" + fill + "abcd",
        "aws temporary key": "ASIA" + "ABCDEFGHIJKLMNOP",
        "google api key": "AIza" + "SyA1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q",
        "lowercase bearer": "authorization: bearer " + fill,
        "basic auth header": "Authorization: Basic " + fill + "==",
        "credentials in url": "scheme" + ":" + "//user" + ":" + "hunter2pass" + "@" + "host/x",
        "assigned api key": "api_key = " + fill,
        "quoted secret": "\"client_secret\": \"" + fill + "\"",
        "jwt": "eyJ" + "hbGciOiJIUzI1NiJ9" + "." + "eyJzdWIiOiIxMjM0NTY3ODkw",
        "zero width split": "sk-" + fill[:6] + zero_width + fill[6:],
        "fullwidth prefix": "gh" + "p_" + fill + "abcdefgh",
        "fullwidth letter": "s" + fullwidth_k + "-" + fill,
    }
    for name, text in secret_cases.items():
        if "LEAK_SECRET" not in _scan_rules("message", text):
            rep.error(SELF, 1, "SELFTEST", f"secret case not rejected: {name}")
    for name, text in {
        "placeholder token": "set token = <your-token> and api_key = ${API_KEY}",
        "plain prose": "the token budget and the secret sauce are unrelated words",
    }.items():
        if "LEAK_SECRET" in _scan_rules("message", text):
            rep.error(SELF, 1, "SELFTEST", f"clean text rejected: {name}")

    head = "permissions:\n  contents: read\njobs:\n  a:\n    steps:\n"
    workflow_cases = {
        "expression in run": ("WORKFLOW_RUN_EXPRESSION", head + "      - run: echo ${{ github.event.pull_request.title }}\n"),
        "expression in run block": ("WORKFLOW_RUN_EXPRESSION", head + "      - run: |\n          echo ${{ github.head_ref }}\n"),
        "secrets context": ("WORKFLOW_SECRETS", head + "      - env:\n          A: ${{ secrets.X }}\n"),
        "secrets via index": ("WORKFLOW_SECRETS", head + "      - env:\n          A: ${{ secrets['X'] }}\n"),
        "repository token": ("WORKFLOW_SECRETS", head + "      - env:\n          A: ${{ github.token }}\n"),
        "secrets as a whole": ("WORKFLOW_SECRETS", head + "      - env:\n          A: ${{ toJSON(secrets) }}\n"),
        "unpinned action": ("WORKFLOW_USES", head + "      - uses: actions/checkout@v4\n"),
        "foreign action": ("WORKFLOW_USES", head + "      - uses: evil/act@" + "a" * 40 + "\n"),
        "local action": ("WORKFLOW_USES", head + "      - uses: ./local\n"),
        "uses value on next line": ("WORKFLOW_USES", head + "      - uses:\n          evil/act@v1\n"),
        "escaped key": ("WORKFLOW_STYLE", head + "      - \"\\x75ses\": evil/act@v1\n"),
        "flow mapping step": ("WORKFLOW_STYLE", head + "      - { uses: evil/act@v1 }\n"),
        "alias value": ("WORKFLOW_STYLE", head + "      - name: *shared\n"),
        "anchor": ("WORKFLOW_STYLE", head + "      - &a name: x\n"),
        "merge key": ("WORKFLOW_STYLE", head + "      - <<: *base\n"),
        "second document": ("WORKFLOW_STYLE", head + "---\npermissions: write-all\n"),
        "tab indentation": ("WORKFLOW_STYLE", head + "      - name: x\n\t  run: echo\n"),
        "carriage return line break": ("WORKFLOW_STYLE", head + "      - name: x\r      run: echo\n"),
        "carriage return inside run block": ("WORKFLOW_STYLE", head + "      - run: |\n          echo\r      - uses: evil/act@v1\n"),
        "line separator inside run block": ("WORKFLOW_STYLE", head + "      - run: |\n          echo" + chr(0x2028) + "      - uses: evil/act@v1\n"),
        "job id run": ("WORKFLOW_USES", "permissions:\n  contents: read\njobs:\n  run:\n    steps:\n      - uses: evil/act@v1\n"),
        "job id script": ("WORKFLOW_PERMISSIONS", "permissions:\n  contents: read\njobs:\n  script:\n    permissions: write-all\n"),
        "look-alike letters": ("WORKFLOW_STYLE", head + "      - " + chr(0xFF55) + "ses: evil/act@v1\n"),
        "zero width in key": ("WORKFLOW_STYLE", head + "      - us" + zero_width + "es: evil/act@v1\n"),
        "pull_request_target": ("WORKFLOW_TRIGGER", "on:\n  pull_request_target:\n" + head),
        "workflow_run": ("WORKFLOW_TRIGGER", "on:\n  workflow_run:\n" + head),
        "write permission": ("WORKFLOW_PERMISSIONS", "permissions:\n  contents: read\njobs:\n  a:\n    permissions:\n      contents: write\n"),
        "write-all": ("WORKFLOW_PERMISSIONS", "permissions: write-all\n"),
        "extra top-level scope": ("WORKFLOW_PERMISSIONS", "permissions:\n  contents: read\n  id-token: write\n"),
        "no top-level permissions": ("WORKFLOW_PERMISSIONS", "jobs:\n  a:\n    steps:\n      - run: echo\n"),
    }
    for name, (rule, text) in workflow_cases.items():
        if rule not in _workflow_rules(text):
            rep.error(SELF, 1, "SELFTEST", f"workflow case not rejected: {name}")
    clean = (head + "      - uses: actions/checkout@" + "a" * 40 + " # v1\n"
             "      - name: Build\n        run: |\n          ls *.md && echo done # a comment\n"
             "        env:\n          V: ${{ github.event_name }}\n")
    if _workflow_rules(clean):
        rep.error(SELF, 1, "SELFTEST", "clean workflow case was rejected")

# ---------------------------------------------------------------------------
# (10) version
# ---------------------------------------------------------------------------
def check_version_only(rep: Report):
    return check_versions(rep)


# ---------------------------------------------------------------------------
# (11) validate
# ---------------------------------------------------------------------------
class Validator:
    """Runs `claude plugin validate --strict` on each manifest file with a throwaway config dir."""

    def __init__(self) -> None:
        self.config_dir = tempfile.mkdtemp(prefix="creagen-claude-config-")
        self.runner: list[str] | None = None
        self.problems: list[tuple[str, int, str, str]] = []
        self.env = dict(os.environ, CLAUDE_CONFIG_DIR=self.config_dir, CI="1", TERM="dumb")

    def close(self) -> None:
        shutil.rmtree(self.config_dir, ignore_errors=True)

    def _run(self, command: list[str], timeout: int):
        return subprocess.run(command, cwd=str(ROOT), env=self.env, capture_output=True, text=True,
                              errors="replace", timeout=timeout)

    def resolve(self) -> bool:
        """Pick the CLI (local binary at the pinned version, else npx) and print its version first."""
        wanted = os.environ.get("CLAUDE_CODE_VERSION", "").strip()
        if not wanted:
            pin = ROOT / VERSION_PIN_FILE
            wanted = pin.read_text(encoding="utf-8").split("\n", 1)[0].strip() if pin.exists() else ""
        if not VERSION_PIN_RE.match(wanted):
            self.problems.append((VERSION_PIN_FILE, 1, "VALIDATE_VERSION_PIN",
                                  "the first line must be an exact version such as 2.1.285 (or latest via CLAUDE_CODE_VERSION)"))
            return False
        try:
            local = shutil.which("claude")
            if local and wanted != "latest":
                first = self._run([local, "--version"], 120).stdout.strip()
                if first.split(" ", 1)[0] == wanted:
                    self.runner = [local]
                    print(first)
                    return True
            npx = shutil.which("npx")
            if not npx:
                self.problems.append(("check.py", 1, "VALIDATE_NO_NODE", "install Node 22 or run with --no-claude"))
                return False
            runner = [npx, "--yes", f"@anthropic-ai/claude-code@{wanted}"]
            result = self._run(runner + ["--version"], 900)
            if result.returncode != 0 or not result.stdout.strip():
                self.problems.append(("check.py", 1, "VALIDATE_RUNNER",
                                      "could not start the Claude CLI (check network access or run with --no-claude)"))
                return False
            self.runner = runner
            print(result.stdout.strip())
            return True
        except (OSError, subprocess.TimeoutExpired):
            self.problems.append(("check.py", 1, "VALIDATE_RUNNER",
                                  "could not start the Claude CLI (check network access or run with --no-claude)"))
            return False

    def describe(self, arguments: list[str]) -> str:
        assert self.runner is not None
        shown = ["claude"] if len(self.runner) == 1 else ["npx"] + self.runner[1:]
        return "+ " + " ".join(shown + arguments)

    def run(self, rep: Report) -> None:
        if self.runner is None:
            return
        for target in VALIDATE_TARGETS:
            arguments = ["plugin", "validate", "--strict", target]
            print(self.describe(arguments))
            start = len(rep.items)
            try:
                result = self._run(self.runner + arguments, 600)
            except (OSError, subprocess.TimeoutExpired):
                rep.error(target, 1, "VALIDATE_RUNNER", "the validator did not finish")
            else:
                if result.returncode == 0:
                    print("  passed")
                    continue
                self.report_failure(rep, target, arguments)
            print("  failed")
            for item in rep.items[start:]:
                print(render(item))

    def report_failure(self, rep: Report, target: str, arguments: list[str]) -> None:
        found = 0
        try:
            detail = self._run(self.runner + arguments + ["--json"], 600)
            data = json.loads(detail.stdout)
            groups = [data.get("manifest")] + list(data.get("contents") or [])
            for group in groups:
                if not isinstance(group, dict):
                    continue
                file = relative_to_root(str(group.get("file") or target))
                for severity in ("errors", "warnings"):
                    for issue in group.get(severity) or []:
                        where = str(issue.get("path") or "")
                        message = str(issue.get("message") or "")[:300]
                        rep.error(file, 1, "CLAUDE_VALIDATE", f"{where}: {message}".strip(": "))
                        found += 1
        except (OSError, subprocess.TimeoutExpired, ValueError, AttributeError):
            pass
        if not found:
            rep.error(target, 1, "CLAUDE_VALIDATE", "the validator failed; run it locally with the same target")


def relative_to_root(path: str) -> str:
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except (ValueError, OSError):
        return Path(path).name


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def emit(rep: Report, start: int, name: str) -> None:
    fresh = rep.items[start:]
    errors, warnings = counts(fresh)
    if not fresh:
        print(f"== {name}: ok")
        return
    print(f"== {name}: {errors} error(s), {warnings} warning(s)")
    for item in fresh:
        print(render(item))


def run_lint(rep: Report, name: str, function) -> None:
    start = len(rep.items)
    function()
    emit(rep, start, name)


def lint_sections(rep: Report, git_range: str):
    return [
        ("json", lambda: check_json(rep)),
        ("manifests", lambda: check_manifests(rep)),
        ("skills", lambda: check_skills(rep)),
        ("readme", lambda: check_readme(rep)),
        ("links", lambda: check_links(rep)),
        ("leaks", lambda: check_leaks(rep, git_range)),
        ("changelog", lambda: check_changelog(rep)),
        ("tree", lambda: check_tree(rep)),
        ("workflows", lambda: check_workflows(rep)),
        ("selftest", lambda: check_selftest(rep)),
    ]


def run_validate(rep: Report, validator: Validator, resolved: bool) -> None:
    print("== validate: claude plugin validate --strict, one call per manifest file")
    start = len(rep.items)
    for problem in validator.problems:
        rep.error(*problem)
    for item in rep.items[start:]:
        print(render(item))
    if resolved:
        validator.run(rep)


def finish(rep: Report) -> int:
    errors, warnings = counts(rep.items)
    if errors == 0 and warnings == 0:
        print("check.py: ALL OK")
    else:
        print(f"check.py: {errors} error(s), {warnings} warning(s)")
    return 1 if errors else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="check.py", description="Lint the Creagen plugin repository.")
    parser.add_argument(
        "subcommand", nargs="?",
        choices=["json", "manifests", "skills", "readme", "links", "leaks", "changelog", "tree", "workflows",
                 "selftest", "version", "validate"],
    )
    parser.add_argument("--all", action="store_true", help="run every check")
    parser.add_argument("--no-claude", action="store_true", help="with --all: skip the Claude validator")
    parser.add_argument("--git-range", default="", help="A...B; scan commit messages in the range (leaks)")
    parser.add_argument("--print", dest="print_version", action="store_true", help="version: print only the version")
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if bool(args.all) == bool(args.subcommand):
        parser.error("give exactly one of a subcommand or --all")
    if args.no_claude and not args.all:
        parser.error("--no-claude only applies to --all")
    if args.print_version and args.subcommand != "version":
        parser.error("--print only applies to the version subcommand")
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    rep = Report()
    try:
        repo_files()
    except GitError:
        print("check.py: run this inside a git checkout (git is required)")
        return 2

    if args.subcommand == "version":
        version = check_version_only(rep)
        errors, _ = counts(rep.items)
        if errors:
            print("\n".join(render(i) for i in rep.items), file=sys.stderr)
            return 1
        if args.print_version:
            print(version)
            return 0
        emit(rep, 0, "version")
        print(f"version: {version}")
        return finish(rep)

    validator = None
    resolved = False
    wants_validate = args.subcommand == "validate" or (args.all and not args.no_claude)
    try:
        if wants_validate:
            validator = Validator()
            resolved = validator.resolve()
        if args.all:
            for name, function in lint_sections(rep, args.git_range):
                run_lint(rep, name, function)
        elif args.subcommand != "validate":
            sections = dict(lint_sections(rep, args.git_range))
            run_lint(rep, args.subcommand, sections[args.subcommand])
        if wants_validate:
            run_validate(rep, validator, resolved)
    finally:
        if validator is not None:
            validator.close()
    return finish(rep)


if __name__ == "__main__":
    sys.exit(main())
