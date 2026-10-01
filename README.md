# Expanse website

The product site for [Expanse](https://github.com/team-expanse/expanse), a
NixOS-based cluster operating system, published at <https://expanseos.org/>.
Plain HTML + CSS + a little vanilla JavaScript: no build step, no external
requests, works opened straight from disk.

## Structure

| Path | What it is |
|---|---|
| `index.html` | Landing page: hero, mock web console and tty1 host console, feature grid, how it works, CLI showcase, honest comparison, CTA |
| `features.html` | Every shipped capability in depth, plus what is deliberately not built yet |
| `docs/getting-started.html` | Quickstart derived from the project's `docs/INSTALL.md` |
| `download.html` | Latest release (1.1.9), build-from-source, requirements, changelog, known issues |
| `assets/site.css` | The whole design system: tokens, light/dark themes, components |
| `assets/site.js` | Theme toggle, mobile nav, copy buttons, scroll reveal, TOC highlight |
| `assets/fonts/` | Self-hosted Inter and JetBrains Mono (OFL; licences alongside) |
| `assets/logo.svg` | Favicon / mark |
| `tools/screenshots.py` | Serves the site and captures review screenshots with Playwright |
| `tools/sync-release` | Release hook: syncs the site to a new Expanse release (see below) |
| `screenshots/` | The captured PNGs |
| `CNAME` | The custom domain GitHub Pages serves the site on |

Every page carries its own copy of the header, footer and inline SVG icon sprite,
so pages stay self-contained and there is nothing to assemble.

The download button points at the GitHub release asset
(`https://github.com/team-expanse/expanse/releases/download/v1.1.9/expanse-1.1.9-x86_64-linux.iso`).
The release hook below keeps it, and every other version mention, current.

## Preview

```sh
python3 -m http.server 8000
# open http://localhost:8000/
```

Opening `index.html` directly from the filesystem also works.

## Screenshots

```sh
PLAYWRIGHT_BROWSERS_PATH=<playwright browsers dir> python3 tools/screenshots.py
```

Needs Python with the `playwright` package and a Chromium build. The script
writes into `screenshots/`, fails on any browser console error, failed request
or horizontal overflow, and cleans up its own HTTP server.

## Releases

Expanse's `scripts/release.sh` publishes a release, then runs
`tools/sync-release <expanse>/dist/<version>/` here. The hook reads that
directory's `release.json` and `notes.md` and:

- bumps the version everywhere except the changelog history;
- refreshes the hero badge, the release card (summary, date, ISO size and SHA-256)
  and the download link;
- adds the release notes as the new latest changelog entry;
- commits the result as `release: sync site to <version>`.

Re-running it for an unchanged release changes nothing; if the notes or ISO
changed, it refreshes them. It refuses to commit over
uncommitted edits to the site files. Pass `--no-commit` to only edit the files
for review. It does not push.

```sh
python3 -m unittest discover -s tools   # the hook's tests
```

## Theming

Light and dark follow `prefers-color-scheme`; the header toggle overrides it
and remembers the choice in `localStorage`. Motion is disabled under
`prefers-reduced-motion`.

## How it is made

Expanse and this website are a joint human–AI effort: a human maintainer
working with AI coding assistants. The site says so on every page (footer) and
in the landing page's "How Expanse is made" section. Most commits credit the AI
co-author in a `Co-Authored-By` trailer. The disclosure deliberately names no
model, vendor or tool, since those change over time; the commits record them.

## License

The site is licensed under the [Apache License, Version 2.0](LICENSE); see
[`NOTICE`](NOTICE). The self-hosted fonts in `assets/fonts/` are under the SIL
Open Font License 1.1, with their licence files alongside.
