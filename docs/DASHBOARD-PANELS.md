---
id: 32baccbf-aaf3-46a3-9449-c892bdb5452e
slug: linear-dashboards-panel-guide
entity: holdingco
---

# Linear Dashboards — Panel Guide

**How to read every panel** across HoldingCo's four Linear observability surfaces:
the three Grafana `linear-*` dashboards and the standalone
[linear.holdingco.com](https://linear.holdingco.com) static site.

> **One rule for all of them:** every number is clickable. Each KPI, bar segment, and
> table row deep-links to the exact saved [Linear](https://linear.app/holdingco11) view
> (or single issue) it summarizes. The dashboards are a *read-optimized front door* to
> Linear — click any figure to see the underlying issue list, never a dead end.

---

## The two systems at a glance

| Surface | URL | Source of truth | Refresh | Data path |
|---|---|---|---|---|
| **Grafana — Ledger Overview** | `grafana.holdingco.com/d/linear-overview` | Prometheus + InfluxDB (`linear` bucket) | 1 min | metrics exporter → Prometheus/Influx → Grafana |
| **Grafana — Flow & Throughput** | `grafana.holdingco.com/d/linear-flow` | same | 1 min | same |
| **Grafana — Backlog Health** | `grafana.holdingco.com/d/linear-backlog` | same | 1 min | same |
| **linear.holdingco.com** | `https://linear.holdingco.com` (LAN-only) | Linear GraphQL API, live | rebuilt every 30 min | 1 GraphQL query → Python renders static HTML |

**Key difference in what you're looking at:**
- **Grafana** panels are *time-series*: they plot how a metric moved over the selected
  window (default `now-30d`). Good for trends, percentiles, and "is it getting better."
- **linear.holdingco.com** is a *point-in-time snapshot* rebuilt every 30 minutes. Good
  for "what does the board look like right now" and a fast clickable index into Linear.

Both read the same team (`holdingco11` / team key `HC`). Grafana reads pre-computed
metrics; the site queries Linear directly, so on rare occasions the site can be up to
~30 min fresher than the last metric scrape (or vice-versa).

---

# Part 1 — Grafana dashboards

Canonical JSON lives at `~/Docker/log-server/dashboards-linear/0{1,2,3}-*.json`,
bind-mounted read-only into Grafana and re-provisioned every 30 s. All three share the
`linear` / `ledger` tag set, a default time range of **last 30 days**, and a **1-minute**
refresh.

### Reading conventions
- **Stat panels** show a single current value; color = threshold band (green good →
  red bad, per panel). Click the number → the matching Linear saved view.
- **Gauges** map a value onto a colored arc against thresholds.
- **Time-series** plot the metric over the dashboard window; hover for exact values,
  p50/p90 pairs share a panel so you can see the spread.
- **Bar / pie charts** break a total down by a dimension (state, priority, project,
  assignee, label, subsidiary). Segments are **not** individually clickable (Linear
  category URLs need slugs, not names) — the whole panel links to the grouped view.
- Metric names beginning `linear_*` are the exported Prometheus series; the Stalled
  table is a raw **Flux/InfluxDB** query against `linear_issue_snapshot`.

---

## 1. Linear Ledger — Overview (`linear-overview`)

The "is the machine healthy today" board. Five headline stats, a burn gauge, a
throughput trend, and three distribution charts.

| Panel | Type | Metric | How to read it |
|---|---|---|---|
| **Open issues** | stat | `linear_issues_open_total` | Everything not completed/canceled. The size of the board. → *Open backlog* view. |
| **In progress** | stat | `sum(linear_issues_by_state{state_type="started"})` | Active WIP right now. Watch for creep. → *WIP started* view. |
| **Completed 24h** | stat | `linear_issues_completed_24h` | Issues closed in the last day — daily pulse. → *Completed 24h* view. |
| **Completed 7d** | stat | `linear_issues_completed_7d` | Weekly output. → *Completed 7d* view. |
| **Stalled (>14d)** | stat | `linear_issues_stalled_total` | Open issues with no state change in 14+ days. **Lower is better**; a rising number = neglected work. → *Stalled >14d* view. |
| **Burn-rate ratio (7d/30d)** | gauge | `linear_burn_rate_ratio` | Recent weekly completion pace vs. the 30-day baseline. **≈1.0 = steady**, **>1 = accelerating**, **<1 = slowing down**. → *Completed 30d* view. |
| **Throughput — created vs completed (per day)** | timeseries | `created_7d/7`, `completed_7d/7`, `completed_30d/30` | Daily arrival vs. completion rates. If the created line sits above completed, the backlog is growing. → *All issues*. |
| **Open issues by subsidiary** | piechart | `topk(8, linear_issues_by_label{label=~".*\.(com\|org\|md\|sh\|ai\|io\|net\|app\|bot\|codes)"})` | Where open work is concentrated across the domain portfolio (labels that look like a domain). → *Open backlog grouped by label*. |
| **Open issues by state** | barchart | `linear_issues_by_state` | Distribution across workflow states (backlog / unstarted / started / …). → *Open backlog grouped by state*. |
| **Source mix (Claude vs human)** | barchart | `linear_issues_by_label{label=~"Source/.*"}` | How much of the backlog was filed by the agent vs. people (the `Source/*` labels). → *Open backlog grouped by label*. |

---

## 2. Linear Ledger — Flow & Throughput (`linear-flow`)

The DORA-style flow board: rates, backlog delta, and the cycle/lead/WIP-age percentile
trio. This is where you diagnose *why* the backlog is moving the way it is.

| Panel | Type | Metric | How to read it |
|---|---|---|---|
| **Burn rate 7d (per day)** | stat | `linear_burn_rate_7d` | Avg issues completed/day over 7 days. → *Completed 7d*. |
| **Burn rate 30d (per day)** | stat | `linear_burn_rate_30d` | Same over 30 days — the baseline pace. → *Completed 30d*. |
| **Arrival rate 7d (per day)** | stat | `linear_arrival_rate_7d` | Avg issues *created*/day over 7 days. Compare against burn rate. → *Created 7d*. |
| **Net backlog Δ/day (7d)** | stat | `linear_net_backlog_change_7d` | Arrival − burn. **Negative = backlog shrinking (good)**, positive = growing. → *Open backlog*. |
| **Burn-rate ratio** | gauge | `linear_burn_rate_ratio` | Same 7d/30d pace ratio as Overview (≈1 steady). → *Completed 30d*. |
| **Cycle time (p50 / p90), last 30d completed** | timeseries | `linear_cycle_time_seconds_p50` / `_p90` | Time from *work started* → done. p50 = typical, p90 = worst-case tail. Rising p90 = a few items dragging. → *Completed 30d*. |
| **Lead time (p50 / p90), last 30d** | timeseries | `linear_lead_time_seconds_p50` / `_p90` | Time from *created* → done (includes wait-in-backlog). Lead ≫ cycle means work waits before it starts. → *Completed 30d*. |
| **WIP age — open issues (p50 / p90)** | timeseries | `linear_wip_age_seconds_p50` / `_p90` | How old currently-open work is. Growing = aging WIP not being finished. → *WIP started*. |
| **WIP by state (stacked)** | timeseries | `sum by (state) (linear_issues_by_state)` | Stacked count of open issues per state over time — see whether work piles up in one column. → *Open backlog*. |
| **Created vs completed totals (last 30d window)** | timeseries | `linear_issues_created_30d`, `linear_issues_completed_30d` | The 30-day totals (not per-day). Gap between the two lines is net backlog change. → *All issues*. |

> **Note on units:** the `*_seconds_*` metrics are stored in seconds; Grafana formats
> them to human units on the panel. p50/p90 always appear as a pair — read them together,
> the gap is your consistency signal.

---

## 3. Linear Ledger — Backlog Health (`linear-backlog`)

The hygiene + composition board. Six stats (three of them **data-quality** checks), four
breakdown bar charts, and the per-issue **Stalled** table.

| Panel | Type | Metric | How to read it |
|---|---|---|---|
| **Total open** | stat | `linear_issues_open_total` | Board size. → *Open backlog*. |
| **Stalled >14d** | stat | `linear_issues_stalled_total` | Untouched 14+ days. **Lower better.** → *Stalled >14d*. |
| **Missing area label** | stat | `linear_issues_unlabeled{axis="area"}` | Hygiene gap: open issues with no `Area/*` label. Should trend to 0. → *Missing area* view. |
| **Missing subsidiary** | stat | `linear_issues_unlabeled{axis="subsidiary"}` | Open issues with no `Subsidiary/*` label. → *Missing subsidiary* view. |
| **Missing source** | stat | `linear_issues_unlabeled{axis="source"}` | Open issues with no `Source/*` label. → *Missing source* view. |
| **WIP age p90** | stat | `linear_wip_age_seconds_p90` | The tail age of open work as a single number — quick "is anything rotting" check. → *WIP started*. |
| **Priority pyramid** | barchart | `linear_issues_by_priority` | Count per priority (Urgent→None). Healthy shape is a pyramid (few urgent, many low); an inverted/heavy-urgent shape = over-escalation. → *grouped by priority*. |
| **Open issues by project (top)** | barchart | `topk(15, linear_issues_by_project)` | Top 15 projects by open count — where the work lives. → *grouped by project*. |
| **Per-assignee load (top)** | barchart | `topk(15, linear_issues_by_assignee)` | Top 15 assignees by open count — spot overload/imbalance. → *grouped by assignee*. |
| **Top labels in backlog** | barchart | `topk(20, linear_issues_by_label)` | 20 most common labels — thematic makeup of the backlog. → *grouped by label*. |
| **Stalled issues (Influx — time-in-state > 14d)** | table | Flux query on `linear_issue_snapshot`, `time_in_state_seconds > 1209600` | The actual stalled issues, columns: `issue_id, state, project, assignee, priority, _value` (seconds in state). **The `issue_id` column deep-links each row to that specific Linear issue.** Panel header → *Stalled >14d* view. |

> `1209600` seconds = 14 days. The table is the only panel that shows individual issues;
> everything else is aggregate.

---

# Part 2 — linear.holdingco.com (static snapshot site)

A single self-contained HTML page (`dist/index.html`) rebuilt every 30 minutes by
`src/build.py` from one cursor-paginated Linear GraphQL query. Chart.js is loaded from
CDN at view time; the page itself contains **no secrets** and is safe to serve. LAN-only
(Pi-hole wildcard + Traefik). Every KPI and both table's rows are clickable
(`config.json` → `views` map; unmapped numbers fall back to the team's `all`/`backlog`
view).

Sections top-to-bottom:

### A. KPI header row
| KPI | Computed as | How to read |
|---|---|---|
| **Total** | `len(issues)` | Every issue ever, for this team. → team *all* view. |
| **Open** | not completed & not canceled | Live board size. Sub-counts **In progress** (`state.type == started`) and **Backlog** (`state.type == backlog`) link to their own views. |
| **Completed** | `state.type == completed` | Lifetime completed count. → *completed* view. |
| **Canceled** | `state.type == canceled` | Lifetime canceled. → *canceled* view. |
| **Completion %** | `completed / total × 100` | Share of all issues that reached done. |

### B. Created / Closed counters
Three-and-three counters, each clickable to a relative-date Linear view:
- **Created today / 7d / 30d** — new issues in the trailing `-P1D / -P7D / -P30D` window.
- **Closed today / 7d / 30d** — issues completed in the same windows.
- **Net 30d** = `created_30d − closed_30d`. Positive = backlog grew this month; negative
  = it shrank. Links to the *created 30d* view.

### C. Burn rate & velocity
- **Burn rate** = average issues closed per week over the trailing **8 weeks**
  (`burn_weeks`), rounded. → *burn* view (completed-30d).
- **Weeks-to-clear** = `open ÷ burn_rate` — a rough ETA to empty the current backlog at
  today's pace (blank if burn rate is 0).
- **12-week velocity chart** (Chart.js) — created vs. closed per week; the visual version
  of Grafana's throughput panel but weekly and snapshot-based.

### D. Distributions
- **By state** — count per workflow state name (`state_counts`).
- **Priority** — count per priority bucket (Urgent/High/Medium/Low/None via `prio_counts`).
- **Top labels** — the 10 most common labels (`label_counts.most_common(10)`).

### E. Tables
- **Most recent issues** — newest `recent_limit` (15) issues by `createdAt`, with
  identifier, title, state, priority, created date. **Each row deep-links to the issue**
  (Linear returns each issue's own URL — no config needed).
- **Stale watch list** — open issues older than `stale_days` (**14**) by created date,
  capped at `stale_limit` (10), oldest first. Rows deep-link to the issue; the section
  header → *stale* view. This is the site's analog of Grafana's Stalled table.

> **Config knobs** (`config.json`): `stale_days`, `recent_limit`, `stale_limit`,
> `burn_weeks`, and the whole `views` URL map. Because `config.json` is bind-mounted
> read-only into the builder, edits take effect on the **next 30-minute rebuild** with no
> image rebuild.

---

## Cross-reference: shared saved views

Both systems point at the same Linear saved views (the slug trailing-ID is what matters;
the prefix is decorative). The common ones:

| Concept | View slug |
|---|---|
| Open backlog | `backlog-open-0604a0155476` |
| WIP started | `wip-started-81d82ab85ac3` |
| Stalled >14d | `backlog-stalled-14d-97a01995805b` |
| Completed 24h / 7d / 30d | `ledger-completed-24h-6a91f95ab95a` / `-7d-fd917fc1a9db` / `-30d-ad40bad6acc9` |
| Created 24h / 7d / 30d | `ledger-created-24h-32f74c53c16f` / `-7d-36c9cfacedd8` / `-30d-eaa2afff8dfe` |
| Missing area / subsidiary / source | `backlog-missing-area-label-32c85ca9ea3b` / `-subsidiary-f7346201bc1a` / `-source-007e2f8287e0` |
| Canceled | `ledger-canceled-afc409e566f9` |
| All issues | `all-issues-781a315a7287` |

New views are created with the `customViewCreate` GraphQL mutation
(`teamId=9f30599b-79c2-4750-a738-5ab8f80e085a`); relative-date filters like
`{"and":[{"completedAt":{"gte":"-P7D"}}]}` work.

---

## Quick "which panel answers my question" index

| Question | Look at |
|---|---|
| How big is the backlog right now? | Overview → *Open issues* · site → *Open* |
| Are we keeping up with incoming work? | Flow → *Net backlog Δ/day* · site → *Net 30d* |
| Is throughput speeding up or slowing? | any → *Burn-rate ratio* gauge |
| Is work getting stuck / aging? | Flow → *WIP age*, *Cycle/Lead p90* |
| What's neglected? | Backlog Health → *Stalled table* · site → *Stale watch list* |
| Is our labeling clean? | Backlog Health → *Missing area/subsidiary/source* |
| Who's overloaded / where's the work? | Backlog Health → *Per-assignee*, *By project* |
| How much is the agent filing? | Overview → *Source mix* |
| What just came in? | site → *Most recent issues* |

---

### Provenance
- Grafana dashboard tracking: [HC-276](https://linear.app/holdingco11/issue/HC-276), [HC-1208](https://linear.app/holdingco11/issue/HC-1208) (all panels clickable)
- linear.holdingco.com site: [HC-1398](https://linear.app/holdingco11/issue/HC-1398) (deploy), [HC-1506](https://linear.app/holdingco11/issue/HC-1506) (clickable KPIs + public config)
- Sources: `~/Docker/log-server/dashboards-linear/0{1,2,3}-*.json` · `linear-dashboard/src/build.py` + `config.json`

_Generated 2026-08-11 · Claude session 32baccbf-aaf3-46a3-9449-c892bdb5452e_
