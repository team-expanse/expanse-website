"""Bring the site up to date with a staged Expanse release (dist/<version>/ from expanse's scripts/release.sh)."""
import html
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

SITE_FILES = ["index.html", "features.html", "download.html", "docs/getting-started.html", "README.md"]


class SyncError(Exception):
    pass


@dataclass(frozen=True)
class Release:
    version: str
    date: str
    summary: str
    iso_url: str
    iso_sha256: str
    iso_size: int
    notes_md: str

    @classmethod
    def from_manifest(cls, m: dict, notes_md: str) -> "Release":
        checks = {
            "version": (m.get("version", ""), r"\d+\.\d+\.\d+"),
            "date": (m.get("date", ""), r"\d{4}-\d{2}-\d{2}"),
            "iso.sha256": (m.get("iso", {}).get("sha256", ""), r"[0-9a-f]{64}"),
            "iso.url": (m.get("iso", {}).get("url", ""), r"https://\S+"),
        }
        for field, (value, pattern) in checks.items():
            if not re.fullmatch(pattern, str(value)):
                raise SyncError(f"release.json: bad {field}: {value!r}")
        if m.get("tag") != "v" + m["version"]:
            raise SyncError(f"release.json: tag {m.get('tag')!r} does not match version {m['version']}")
        title = m.get("title", "")
        return cls(m["version"], m["date"], title.split(": ", 1)[-1], m["iso"]["url"],
                   m["iso"]["sha256"], int(m["iso"]["size"]), notes_md)


def load_release(release_dir: Path) -> Release:
    manifest = json.loads((release_dir / "release.json").read_text())
    notes = (release_dir / manifest.get("notes", "notes.md")).read_text()
    return Release.from_manifest(manifest, notes)


def inline(text: str) -> str:
    """Render inline Markdown: `code`, **bold** and [text](url); everything else is escaped."""
    out = []
    for i, part in enumerate(re.split(r"`([^`]+)`", text)):
        if i % 2:
            out.append(f"<code>{html.escape(part, quote=False)}</code>")
            continue
        part = html.escape(part, quote=False)
        part = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)",
                      lambda m: f'<a href="{m.group(2).replace(chr(34), "&quot;")}">{m.group(1)}</a>', part)
        out.append(re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", part))
    return "".join(out)


def markdown_to_html(md: str) -> str:
    """Render the changelog subset of Markdown: headings, bullet lists and paragraphs."""
    out, item, para, in_list = [], None, None, False

    def flush():
        nonlocal item, para
        if item is not None:
            out.append(f"  <li>{inline(item)}</li>")
        if para is not None:
            out.append(f"<p>{inline(para)}</p>")
        item = para = None

    def close_list():
        nonlocal in_list
        flush()
        if in_list:
            out.append("</ul>")
        in_list = False

    for line in md.splitlines():
        stripped = line.strip()
        bullet = re.match(r"[-*] (.*)", stripped)
        if not stripped:
            flush()
        elif stripped.startswith("#"):
            close_list()
            out.append(f"<h4>{inline(stripped.lstrip('#').strip())}</h4>")
        elif bullet:
            flush()
            if not in_list:
                out.append("<ul>")
                in_list = True
            item = bullet.group(1)
        elif item is not None:
            item += " " + stripped
        else:
            if in_list:
                close_list()
            para = stripped if para is None else para + " " + stripped
    close_list()
    return "\n".join(out)


def _outside_changelog(text: str, fn) -> str:
    """Apply fn to the text outside <details class="rel..."> changelog entries, which are history."""
    parts = re.split(r'(<details class="rel[^"]*"[^>]*>.*?</details>)', text, flags=re.S)
    return "".join(p if i % 2 else fn(p) for i, p in enumerate(parts))


def bump_version(text: str, old: str, new: str) -> str:
    """Replace old with new, re-padding a following run of spaces so fixed-width columns stay aligned."""
    pattern = re.compile(r"(?<![\d.])" + re.escape(old) + r"(?!\d|\.\d)( {2,})?")

    def repl(m: re.Match) -> str:
        pad = m.group(1) or ""
        if pad:
            pad = " " * max(1, len(pad) - (len(new) - len(old)))
        return new + pad

    return _outside_changelog(text, lambda part: pattern.sub(repl, part))


def update_release_details(text: str, rel: Release) -> str:
    """Refresh the hero badge, release card summary, ISO size and checksum, outside the changelog history."""
    summary = html.escape(rel.summary, quote=False)
    headline = summary[:1].upper() + summary[1:]

    def refresh(part: str) -> str:
        part = re.sub(r'(<span class="tag">[^<]*</span>\s*<span>)[^<]*(</span>)', rf"\g<1>{headline}\g<2>", part)
        part = re.sub(r'(<div class="date">Released )[^<]*(</div>)', rf"\g<1>{rel.date} · {summary}\g<2>", part)
        part = re.sub(r"about [\d.]+ GB", f"about {rel.iso_size / 1e9:.1f} GB", part)
        return re.sub(r'(<code class="sha256">)[0-9a-f]*(</code>)', rf"\g<1>{rel.iso_sha256}\g<2>", part)

    return _outside_changelog(text, refresh)


def add_changelog_entry(text: str, rel: Release) -> str:
    """Insert the release as the open, latest changelog entry, replacing any earlier entry for the version."""
    existing = re.compile(r' *<details class="rel[^"]*"[^>]*>\s*<summary><span class="ver">'
                          + re.escape(rel.version) + r'</span>.*?</details>\n\n?', re.S)
    text = existing.sub("", text, count=1)
    summary = html.escape(rel.summary, quote=False)
    body = "\n".join("            " + line for line in markdown_to_html(rel.notes_md).splitlines())
    entry = (
        '        <details class="rel latest" open>\n'
        f'          <summary><span class="ver">{rel.version}</span><span>{summary[:1].upper() + summary[1:]}</span>'
        f'<span class="when">{rel.date}</span><svg class="icon chev" aria-hidden="true"><use href="#i-chevron"/></svg></summary>\n'
        '          <div class="rel-body">\n'
        f"{body}\n"
        "          </div>\n"
        "        </details>\n"
    )
    text = text.replace('<details class="rel latest" open>', '<details class="rel">')
    return text.replace('<div class="changelog">\n', '<div class="changelog">\n' + entry + "\n", 1)


def site_version(site: Path) -> str:
    m = re.search(r'<span class="brand-version">([^<]+)</span>', (site / "index.html").read_text())
    if not m:
        raise SyncError("index.html has no brand-version to read the site's current version from")
    return m.group(1)


def _git(site: Path, *args: str, git_config=()) -> str:
    return subprocess.run(["git", "-C", str(site), *git_config, *args], check=True,
                          capture_output=True, text=True).stdout


def sync(site: Path, release_dir: Path, commit: bool = True, git_config=()) -> list:
    """Update the site for the release and return the files changed; commit them if asked (needs clean site files)."""
    rel, old = load_release(release_dir), site_version(site)
    dirty = commit and _git(site, "status", "--porcelain", "--", *SITE_FILES).strip()
    if dirty:
        raise SyncError(f"uncommitted changes in site files; commit or stash them first:\n{dirty}")
    changed = []
    for name in SITE_FILES:
        path = site / name
        before = path.read_text()
        after = update_release_details(bump_version(before, old, rel.version), rel)
        if name == "download.html":
            after = add_changelog_entry(after, rel)
        if after != before:
            path.write_text(after)
            changed.append(name)
    if commit and changed:
        _git(site, "add", "--", *changed)
        _git(site, "commit", "-q", "-m", f"release: sync site to {rel.version}", git_config=git_config)
    return changed
