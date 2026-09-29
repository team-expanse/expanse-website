# Expanse website

The product site for [Expanse](../expanse), a NixOS-based cluster operating
system. Plain HTML + CSS + a little vanilla JavaScript: no build step, no
external requests, works opened straight from disk.

## Structure

| Path | What it is |
|---|---|
| `index.html` | Landing page: hero, mock web console and tty1 host console, feature grid, how it works, CLI showcase, honest comparison, CTA |
| `features.html` | Every shipped capability in depth, plus what is deliberately not built yet |
| `docs/getting-started.html` | Quickstart derived from the project's `docs/INSTALL.md` |
| `download.html` | Latest release (1.1.6), build-from-source, requirements, changelog, known issues |
| `assets/site.css` | The whole design system: tokens, light/dark themes, components |
| `assets/site.js` | Theme toggle, mobile nav, copy buttons, scroll reveal, TOC highlight |
| `assets/fonts/` | Self-hosted Inter and JetBrains Mono (OFL; licences alongside) |
| `assets/logo.svg` | Favicon / mark |
| `tools/screenshots.py` | Serves the site and captures review screenshots with Playwright |
| `screenshots/` | The captured PNGs |

Every page carries its own copy of the header, footer and inline SVG icon sprite,
so pages stay self-contained and there is nothing to assemble.

The download button points at the GitHub release asset
(`https://github.com/team-expanse/expanse/releases/download/v1.1.6/expanse-1.1.6-x86_64-linux.iso`).
It works once the `v1.1.6` tag is pushed and the ISO is uploaded to that release;
update the version in `download.html` for each new release.

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

## Theming

Light and dark follow `prefers-color-scheme`; the header toggle overrides it
and remembers the choice in `localStorage`. Motion is disabled under
`prefers-reduced-motion`.

## License

The site is licensed under the [Apache License, Version 2.0](LICENSE); see
[`NOTICE`](NOTICE). The self-hosted fonts in `assets/fonts/` are under the SIL
Open Font License 1.1, with their licence files alongside.
