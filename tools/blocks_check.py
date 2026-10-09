"""Check the block reference pages against the block types an Expanse release ships."""
import json
import re
import subprocess
from pathlib import Path

CATALOG = "docs/blocks.html"


def page_path(block_type: str) -> str:
    return "docs/blocks/" + block_type.replace("/", "-", 1) + ".html"


def required_keys(schema: dict) -> set:
    """Top-level config keys plus the keys of array items, which a page must each document."""
    keys = set()
    for name, prop in schema.get("properties", {}).items():
        keys.add(name)
        items = prop.get("items")
        if isinstance(items, dict):
            keys |= {f"{name}[].{k}" for k in items.get("properties", {})}
    return keys


def allowed_keys(schema: dict) -> set:
    """Required keys plus object children, which a page may document in their own rows."""
    keys = required_keys(schema)
    for name, prop in schema.get("properties", {}).items():
        keys |= {f"{name}.{k}" for k in prop.get("properties", {})}
    return keys


def page_keys(html: str) -> list:
    table = re.search(r'<table class="t config"[^>]*>(.*?)</table>', html, re.S)
    return re.findall(r'<tr data-key="([^"]+)"', table.group(1)) if table else []


def check_page(block_type: str, html: str, schema: dict) -> list:
    if '<table class="t config"' not in html:
        return [f"{block_type}: no config table"]
    keys = set(page_keys(html))
    problems = []
    missing = required_keys(schema) - keys
    if missing:
        problems.append(f"{block_type}: config table lacks {', '.join(sorted(missing))}")
    unknown = keys - allowed_keys(schema)
    if unknown:
        problems.append(f"{block_type}: config table documents keys the schema does not have: {', '.join(sorted(unknown))}")
    return problems


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


def shipped_schemas(repo: Path, tag: str) -> dict:
    """Map each block type in nix/blocks at tag to its config schema."""
    files = _git(repo, "ls-tree", "-r", "--name-only", tag, "--", "nix/blocks").split()
    return {f[len("nix/blocks/"):-len("/schema.json")]: json.loads(_git(repo, "show", f"{tag}:{f}"))
            for f in files if f.endswith("/schema.json")}


def check(site: Path, repo: Path, tag: str) -> list:
    """Return every mismatch between the site's block pages and the types shipped at tag."""
    schemas = shipped_schemas(repo, tag)
    catalog = (site / CATALOG).read_text() if (site / CATALOG).exists() else ""
    problems = []
    for block_type, schema in sorted(schemas.items()):
        path = site / page_path(block_type)
        if not path.exists():
            problems.append(f"{block_type}: no page at {page_path(block_type)}")
        else:
            problems += check_page(block_type, path.read_text(), schema)
        if f'href="blocks/{Path(page_path(block_type)).name}"' not in catalog:
            problems.append(f"{block_type}: not linked from {CATALOG}")
    for path in sorted((site / "docs" / "blocks").glob("*.html")):
        block_type = path.stem.replace("-", "/", 1)
        if block_type not in schemas:
            problems.append(f"docs/blocks/{path.name}: no shipped block type {block_type}")
    return problems
