"""Tests for blocks_check. Run: python3 -m unittest discover -s tools"""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import blocks_check as bc

SCHEMA = {
    "type": "object",
    "properties": {
        "port": {"type": "integer"},
        "tls": {"type": "object", "properties": {"cert": {"type": "string"}, "key": {"type": "string"}}},
        "env": {"type": "object"},
        "sites": {"type": "array", "items": {"type": "object", "properties": {"host": {}, "tls": {}}}},
        "buckets": {"type": "array", "items": {"type": "string"}},
    },
}


def page(type_, keys):
    rows = "".join(f'<tr data-key="{k}"><td>{k}</td></tr>' for k in keys)
    return f'<table class="t config" data-block="{type_}"><tbody>{rows}</tbody></table>'


class SchemaKeys(unittest.TestCase):
    def test_required_keys_are_top_level_and_array_items(self):
        self.assertEqual(bc.required_keys(SCHEMA), {"port", "tls", "env", "sites", "buckets", "sites[].host", "sites[].tls"})

    def test_allowed_keys_add_object_children(self):
        self.assertEqual(bc.allowed_keys(SCHEMA) - bc.required_keys(SCHEMA), {"tls.cert", "tls.key"})


class PageKeys(unittest.TestCase):
    def test_reads_the_config_table_rows(self):
        self.assertEqual(bc.page_keys(page("web/x", ["port", "tls.cert"])), ["port", "tls.cert"])

    def test_ignores_rows_outside_the_config_table(self):
        html = '<table class="t"><tr data-key="nope"></tr></table>' + page("web/x", ["port"])
        self.assertEqual(bc.page_keys(html), ["port"])


class PagePath(unittest.TestCase):
    def test_flattens_the_type_into_one_file_name(self):
        self.assertEqual(bc.page_path("db/postgres"), "docs/blocks/db-postgres.html")


class CheckPage(unittest.TestCase):
    def test_a_matching_page_has_no_problems(self):
        keys = ["port", "tls", "tls.cert", "env", "sites", "sites[].host", "sites[].tls", "buckets"]
        self.assertEqual(bc.check_page("web/x", page("web/x", keys), SCHEMA), [])

    def test_reports_missing_and_unknown_keys(self):
        problems = bc.check_page("web/x", page("web/x", ["port", "gone"]), SCHEMA)
        self.assertIn("web/x: config table lacks buckets, env, sites, sites[].host, sites[].tls, tls", problems)
        self.assertIn("web/x: config table documents keys the schema does not have: gone", problems)

    def test_reports_a_page_without_a_config_table(self):
        self.assertEqual(bc.check_page("web/x", "<p>nothing</p>", SCHEMA), ["web/x: no config table"])


class CheckSite(unittest.TestCase):
    def make(self, root: Path, types: dict, pages: dict, catalog_links: list) -> tuple:
        repo, site = root / "repo", root / "site"
        for t, schema in types.items():
            d = repo / "nix" / "blocks" / t
            d.mkdir(parents=True)
            (d / "schema.json").write_text(json.dumps(schema))
        git = ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t"]
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(git + ["add", "-A"], check=True)
        subprocess.run(git + ["commit", "-qm", "init"], check=True)
        subprocess.run(git + ["tag", "v1.0.0"], check=True)
        (site / "docs" / "blocks").mkdir(parents=True)
        links = "".join(f'<a href="blocks/{bc.page_path(t).split("/")[-1]}">{t}</a>' for t in catalog_links)
        (site / "docs" / "blocks.html").write_text(links)
        for t, html in pages.items():
            (site / bc.page_path(t)).write_text(html)
        return site, repo

    def test_clean_site(self):
        with tempfile.TemporaryDirectory() as t:
            site, repo = self.make(Path(t), {"util/echo": {"properties": {"port": {}}}},
                                   {"util/echo": page("util/echo", ["port"])}, ["util/echo"])
            self.assertEqual(bc.check(site, repo, "v1.0.0"), [])

    def test_reports_a_new_type_without_page_or_catalog_entry(self):
        with tempfile.TemporaryDirectory() as t:
            site, repo = self.make(Path(t), {"util/echo": {"properties": {}}, "db/new": {"properties": {}}},
                                   {"util/echo": page("util/echo", [])}, ["util/echo"])
            problems = bc.check(site, repo, "v1.0.0")
        self.assertIn("db/new: no page at docs/blocks/db-new.html", problems)
        self.assertIn("db/new: not linked from docs/blocks.html", problems)

    def test_reports_a_page_for_a_type_no_longer_shipped(self):
        with tempfile.TemporaryDirectory() as t:
            site, repo = self.make(Path(t), {"util/echo": {"properties": {}}},
                                   {"util/echo": page("util/echo", []), "db/old": page("db/old", [])}, ["util/echo"])
            self.assertEqual(bc.check(site, repo, "v1.0.0"), ["docs/blocks/db-old.html: no shipped block type db/old"])


if __name__ == "__main__":
    unittest.main()
