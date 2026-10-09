"""Tests for release_sync. Run: python3 -m unittest discover -s tools"""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import release_sync as rs

RELEASE = {
    "version": "1.1.7",
    "tag": "v1.1.7",
    "date": "2026-09-29",
    "title": "Expanse 1.1.7: licence files, release script",
    "release_url": "https://github.com/team-expanse/expanse/releases/tag/v1.1.7",
    "notes": "notes.md",
    "iso": {
        "name": "expanse-1.1.7-x86_64-linux.iso",
        "url": "https://github.com/team-expanse/expanse/releases/download/v1.1.7/expanse-1.1.7-x86_64-linux.iso",
        "sha256": "ab" * 32,
        "size": 1472069632,
    },
}
NOTES = """### Added

- Ships `LICENSE` & **NOTICE**; see [the docs](https://example.org/a_b).
- A long item that GitHub-style notes keep
  on one line, but wrapped input still joins.

### Fixed

- Nothing < everything.
"""

CHANGELOG = """<div class="changelog">
        <details class="rel latest" open>
          <summary><span class="ver">1.1.6</span><span>Old</span><span class="when">2026-09-28</span></summary>
          <div class="rel-body"><p>Built in 1.1.6.</p></div>
        </details>
      </div>"""


def write_release(tmp: Path, **overrides) -> Path:
    d = tmp / "dist"
    d.mkdir()
    (d / "release.json").write_text(json.dumps({**RELEASE, **overrides}))
    (d / "notes.md").write_text(NOTES)
    return d


class LoadRelease(unittest.TestCase):
    def test_reads_manifest_and_notes(self):
        with tempfile.TemporaryDirectory() as t:
            rel = rs.load_release(write_release(Path(t)))
        self.assertEqual(rel.version, "1.1.7")
        self.assertEqual(rel.summary, "licence files, release script")
        self.assertIn("### Added", rel.notes_md)

    def test_rejects_a_non_semver_version(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(rs.SyncError):
                rs.load_release(write_release(Path(t), version="1.1.7; rm -rf"))


class MarkdownToHtml(unittest.TestCase):
    def test_headings_lists_and_inline_markup(self):
        html = rs.markdown_to_html(NOTES)
        self.assertIn("<h4>Added</h4>", html)
        self.assertIn("<li>Ships <code>LICENSE</code> &amp; <strong>NOTICE</strong>; see "
                      '<a href="https://example.org/a_b">the docs</a>.</li>', html)
        self.assertIn("keep on one line, but wrapped", html)
        self.assertIn("Nothing &lt; everything.", html)
        self.assertEqual(html.count("<ul>"), 2)

    def test_quotes_stay_readable_but_hrefs_stay_safe(self):
        self.assertEqual(rs.inline("the site's \"hook\""), "the site's \"hook\"")
        self.assertEqual(rs.inline('[x](https://e.org/"a)'), '<a href="https://e.org/&quot;a">x</a>')

    def test_markup_inside_code_is_literal(self):
        self.assertEqual(rs.inline("`**x**`"), "<code>**x**</code>")

    def test_paragraphs(self):
        self.assertEqual(rs.markdown_to_html("Just text\nwrapped."), "<p>Just text wrapped.</p>")


class BumpVersion(unittest.TestCase):
    def test_replaces_outside_changelog_only(self):
        html = f'<span class="brand-version">1.1.6</span> v1.1.6 {CHANGELOG} Open in 1.1.6'
        out = rs.bump_version(html, "1.1.6", "1.1.7")
        self.assertIn('<span class="brand-version">1.1.7</span> v1.1.7', out)
        self.assertIn("Open in 1.1.7", out)
        self.assertIn("Built in 1.1.6.", out)

    def test_does_not_touch_longer_versions(self):
        self.assertEqual(rs.bump_version("1.1.60 11.1.6", "1.1.6", "1.1.7"), "1.1.60 11.1.6")

    def test_keeps_fixed_width_columns_aligned(self):
        line = "EXPANSE 1.1.9      2026-09-28"
        self.assertEqual(rs.bump_version(line, "1.1.9", "1.1.10"), "EXPANSE 1.1.10     2026-09-28")
        self.assertEqual(rs.bump_version("EXPANSE 1.1.10     x", "1.1.10", "1.2.0"), "EXPANSE 1.2.0      x")


class AddChangelogEntry(unittest.TestCase):
    def test_new_entry_becomes_the_open_latest(self):
        rel = rs.Release.from_manifest(RELEASE, NOTES)
        out = rs.add_changelog_entry(CHANGELOG, rel)
        self.assertLess(out.index('<span class="ver">1.1.7</span>'), out.index('<span class="ver">1.1.6</span>'))
        self.assertEqual(out.count('class="rel latest" open'), 1)
        self.assertIn('<details class="rel">\n          <summary><span class="ver">1.1.6</span>', out)
        self.assertIn("<span>Licence files, release script</span><span class=\"when\">2026-09-29</span>", out)

    def test_replaces_an_entry_whose_notes_changed(self):
        rel = rs.Release.from_manifest(RELEASE, NOTES)
        staged = rs.add_changelog_entry(CHANGELOG, rs.Release.from_manifest(RELEASE, "- Draft note."))
        out = rs.add_changelog_entry(staged, rel)
        self.assertEqual(out, rs.add_changelog_entry(CHANGELOG, rel))
        self.assertNotIn("Draft note", out)

    def test_is_idempotent(self):
        rel = rs.Release.from_manifest(RELEASE, NOTES)
        once = rs.add_changelog_entry(CHANGELOG, rel)
        self.assertEqual(rs.add_changelog_entry(once, rel), once)


class ReleaseCard(unittest.TestCase):
    CARD = """<span class="tag">1.1.7</span>
          <span>Old summary</span>
<div class="date">Released 2026-09-28 · old summary</div>
<div class="meta">Hybrid UEFI + BIOS installer image · about 1.4 GB · needs a 4 GB USB stick</div>
<code class="sha256">00</code>"""

    def test_updates_summary_date_size_and_checksum(self):
        rel = rs.Release.from_manifest(RELEASE, NOTES)
        out = rs.update_release_details(self.CARD, rel)
        self.assertIn("<span>Licence files, release script</span>", out)
        self.assertIn("Released 2026-09-29 · licence files, release script", out)
        self.assertIn("about 1.5 GB", out)
        self.assertIn(f'<code class="sha256">{"ab" * 32}</code>', out)

    def test_leaves_changelog_history_alone(self):
        rel = rs.Release.from_manifest(RELEASE, NOTES)
        history = CHANGELOG.replace("Built in 1.1.6.", "The ISO grows to about 1.65 GB.")
        self.assertIn("about 1.65 GB", rs.update_release_details(self.CARD + history, rel))


class SiteFiles(unittest.TestCase):
    def test_include_the_block_pages(self):
        with tempfile.TemporaryDirectory() as t:
            site = Path(t)
            (site / "docs" / "blocks").mkdir(parents=True)
            for f in ("docs/blocks.html", "docs/blocks/web-nginx.html", "docs/blocks/db-redis.html"):
                (site / f).write_text("")
            self.assertEqual(rs.site_files(site)[-3:], ["docs/blocks.html", "docs/blocks/db-redis.html", "docs/blocks/web-nginx.html"])
            self.assertEqual(rs.site_files(site)[:len(rs.SITE_FILES)], rs.SITE_FILES)


class BlockProblems(unittest.TestCase):
    def test_none_without_an_expanse_checkout(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(rs.block_problems(Path(t), write_release(Path(t)), "1.1.7"), [])


class EndToEnd(unittest.TestCase):
    def make_site(self, root: Path) -> None:
        (root / "docs").mkdir()
        (root / "index.html").write_text('<span class="brand-version">1.1.6</span>\n' + ReleaseCard.CARD.replace("1.1.7", "1.1.6"))
        (root / "download.html").write_text(f'<a href="{RELEASE["iso"]["url"].replace("1.1.7", "1.1.6")}">x</a>\n{CHANGELOG}')
        (root / "docs" / "getting-started.html").write_text("nix build github:team-expanse/expanse/v1.1.6#iso")
        for f in ("features.html", "README.md"):
            (root / f).write_text("Expanse 1.1.6")
        git = ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t"]
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(git + ["add", "-A"], check=True)
        subprocess.run(git + ["commit", "-qm", "init"], check=True)
        self.git = git

    def test_syncs_then_is_a_no_op(self):
        with tempfile.TemporaryDirectory() as t:
            site, rel_dir = Path(t) / "site", write_release(Path(t))
            site.mkdir()
            self.make_site(site)
            changed = rs.sync(site, rel_dir, commit=False)
            self.assertEqual(sorted(changed), sorted(rs.SITE_FILES))
            self.assertIn('href="' + RELEASE["iso"]["url"], (site / "download.html").read_text())
            self.assertIn("v1.1.7#iso", (site / "docs/getting-started.html").read_text())
            self.assertIn("Built in 1.1.6.", (site / "download.html").read_text())
            subprocess.run(self.git + ["commit", "-qam", "sync"], check=True)
            self.assertEqual(rs.sync(site, rel_dir, commit=False), [])

    def test_refuses_to_commit_over_uncommitted_edits(self):
        with tempfile.TemporaryDirectory() as t:
            site, rel_dir = Path(t) / "site", write_release(Path(t))
            site.mkdir()
            self.make_site(site)
            (site / "features.html").write_text("local edit 1.1.6")
            with self.assertRaises(rs.SyncError):
                rs.sync(site, rel_dir, commit=True)
            self.assertIn("features.html", rs.sync(site, rel_dir, commit=False))

    def test_commits_when_asked(self):
        with tempfile.TemporaryDirectory() as t:
            site, rel_dir = Path(t) / "site", write_release(Path(t))
            site.mkdir()
            self.make_site(site)
            rs.sync(site, rel_dir, commit=True, git_config=["-c", "user.name=t", "-c", "user.email=t@t"])
            log = subprocess.run(self.git + ["log", "-1", "--format=%s"], capture_output=True, text=True).stdout
            self.assertEqual(log.strip(), "release: sync site to 1.1.7")


if __name__ == "__main__":
    unittest.main()
