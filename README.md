---
id: 12ecbed4-ad54-4d85-bf83-53116df80bfe
slug: linear-dashboard-repo-scaffold
entity: holdingco
---

# linear-dashboard

Self-contained HTML dashboard summarising HoldingCo's Linear (`HC`) team:
total / open / completed / canceled, burn rate, 12-week velocity, state &
priority distributions, top labels, most-recent issues, and stale-issue
watch list.

No runtime deps — pure Python stdlib + Chart.js loaded from CDN at view
time.

## Layout

```
linear-dashboard/
├── src/
│   ├── build.py        # fetch + render
│   └── template.html   # CSS/JS template (placeholders: __TOKEN__)
├── dist/               # generated (gitignored)
│   ├── index.html
│   └── issues.json     # last fetched issues (cache)
├── start.sh            # convenience runner
├── requirements.txt    # empty — stdlib only
├── .pre-commit-config.yaml
└── .github/workflows/  # CI + gitleaks
```

## Usage

```bash
./start.sh                  # fetch live + render
./start.sh --from-cache     # re-render without hitting Linear
open dist/index.html
```

## Linear auth

Reads `~/.config/linear/config.json`, key path:

```
workspaces.holdingco11.users.cbergeron.keys.read_only
```

## Roadmap

- Cron the refresh + publish to `linear.holdingco.com` (Traefik static
  site).
- Per-project breakdown panel.
- Cycle-time / time-in-state metrics (need `history` from Linear API).
- Optional Slack digest of the same numbers.

