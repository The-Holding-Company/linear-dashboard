---
id: 881bf590-edb3-4822-812d-59fbb8e7d36a
slug: linear-dashboard-clickable-public
entity: holdingco
---

# linear-dashboard

A self-contained, zero-dependency HTML dashboard for a [Linear](https://linear.app) team:
totals, burn rate, 12-week velocity, state & priority distributions, top labels,
most-recent issues, and a stale-issue watch list — regenerated on a schedule and
served as a single static page.

**Every number is clickable**: KPI values, created/closed counters, and table rows
deep-link to the Linear view or issue they summarize, so the dashboard is a
read-optimized front door to Linear rather than a dead end.

- Pure Python stdlib — no pip installs. Chart.js is loaded from CDN at view time.
- One GraphQL query (cursor-paginated) per build; a read-only Linear API key is all it needs.
- The generated `dist/index.html` contains **no secrets** — safe to serve publicly.

## Quickstart

```bash
cp config.example.json config.json   # edit workspace, team_key, title
export LINEAR_API_KEY=lin_api_...    # a *read-only* key
./start.sh                           # fetch + render
open dist/index.html

./start.sh --from-cache              # re-render without hitting the API
```

## Configuration — `config.json`

All keys are optional; defaults are in `config.example.json`. The file is looked up at
the repo root (override with the `DASHBOARD_CONFIG` env var).

| Key | Default | Purpose |
|---|---|---|
| `workspace` | `your-workspace` | Linear workspace URL slug (`linear.app/<workspace>/…`) |
| `team_key` | `ENG` | Team key whose issues are fetched |
| `title` | `Linear Dashboard` | Page + header title |
| `stale_days` | `14` | Age threshold for the stale-issue table |
| `recent_limit` / `stale_limit` | `15` / `10` | Row caps for the two tables |
| `burn_weeks` | `8` | Trailing window for the burn-rate average |
| `views.*` | `null` | Full Linear URLs backing each clickable number (below) |
| `token_fallback` | — | Optional `{file, json_path}` to read the API key from a local JSON file when `LINEAR_API_KEY` is unset |

### Clickable numbers → `views` map

Each KPI links to the URL configured under `views`; anything left `null` falls back
to the team's built-in `all` view (`backlog` falls back to the team backlog), so the
dashboard is fully functional with zero view setup — configured views just make the
click land on a filtered list that matches the number.

| `views` key | Number it backs | Suggested Linear filter |
|---|---|---|
| `all` | Total issues | — (team all) |
| `open` | Open | state type in backlog/unstarted/started |
| `in_progress` / `backlog` | Open KPI sub-counts | state type started / team backlog |
| `completed` / `canceled` | Completed / Canceled | state type completed / canceled |
| `created_today` `created_7d` `created_30d` | Created counters | `createdAt >= -P1D / -P7D / -P30D` |
| `closed_today` `closed_7d` `closed_30d` | Closed counters | `completedAt >= -P1D / -P7D / -P30D` |
| `burn` | Burn rate | `completedAt >= -P30D` |
| `stale` | Stale table header | open + `updatedAt < -P14D` |

Saved views with relative-date filters are easiest to create via Linear's
`customViewCreate` GraphQL mutation, e.g. `{"and":[{"completedAt":{"gte":"-P7D"}}]}`.
Issue IDs in the tables always deep-link to the issue itself (the API returns each
issue's URL — no configuration needed).

## Linear auth

`LINEAR_API_KEY` env var. Use a **read-only** key: the dashboard only queries
`issues`. The key never appears in the generated HTML. Without the env var,
`token_fallback` (if configured) reads the key from a local JSON config file —
useful for local dev, ignored in containers.

## Deployment (Docker)

Two containers: a `builder` (python:3.13-alpine) renders once at start and then
every 30 minutes via busybox crond into a shared `dist` volume; `web`
(nginx:alpine) serves that volume. The compose file carries
[Traefik](https://traefik.io) labels for HTTPS routing — swap the `Host()` rule
(and network name) for your environment, or delete the labels and publish port 80.

```bash
cp config.example.json config.json   # edit for your workspace
echo "LINEAR_API_KEY=lin_api_..." > .env   # gitignored
docker compose up -d --build
```

`config.json` is gitignored (it names your workspace and saved views) and is
bind-mounted read-only into the builder, so config changes take effect on the next
30-minute rebuild without re-building the image.

> HoldingCo instance: served at https://linear.holdingco.com (LAN, Traefik
> wildcard cert); `.env` is written by `./refresh-env.sh` from OpenBao
> `secret/holdingco/linear` (field `read_only`).

## Layout

```
linear-dashboard/
├── docs/
│   └── DASHBOARD-PANELS.md   # panel-by-panel reading guide (this site + Grafana)
├── src/
│   ├── build.py             # fetch + render (stdlib only)
│   └── template.html        # CSS/JS template (placeholders: __TOKEN__)
├── config.example.json      # copy to config.json (gitignored) and edit
├── docker/entrypoint.sh     # build once, then crond */30
├── docker-compose.yml       # builder + nginx web
├── dist/                    # generated output (gitignored)
│   ├── index.html
│   └── issues.json          # last fetch (cache for --from-cache)
├── start.sh                 # local convenience runner
└── refresh-env.sh           # HoldingCo-specific: OpenBao → .env
```

## Documentation

- **[docs/DASHBOARD-PANELS.md](docs/DASHBOARD-PANELS.md)** — how to read every panel, for
  both this site and the three Grafana `linear-*` dashboards (Overview, Flow &
  Throughput, Backlog Health). Includes a "which panel answers my question" index and the
  shared saved-view slug map.

## Roadmap

- Per-project breakdown panel.
- Cycle-time / time-in-state metrics (needs `history` in the query).
- Optional Slack digest of the same numbers.
