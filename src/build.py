#!/usr/bin/env python3
"""Fetch HoldingCo HC issues from Linear and render a self-contained dashboard."""
import json
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TEMPLATE = HERE / "template.html"
OUT = ROOT / "dist" / "index.html"
CACHE = ROOT / "dist" / "issues.json"
CONFIG = Path.home() / ".config" / "linear" / "config.json"

QUERY = (
    "query{issues(filter:{team:{key:{eq:\"HC\"}}},first:250,orderBy:createdAt)"
    "{nodes{identifier title url createdAt completedAt canceledAt updatedAt "
    "priority estimate state{name type} team{key} "
    "labels{nodes{name}} assignee{name}}}}"
)


def fetch():
    cfg = json.load(CONFIG.open())
    token = cfg["workspaces"]["holdingco11"]["users"]["cbergeron"]["keys"]["read_only"]
    req = urllib.request.Request(
        "https://api.linear.app/graphql",
        data=json.dumps({"query": QUERY}).encode(),
        headers={"Authorization": token, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None


def build():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if "--from-cache" in sys.argv and CACHE.exists():
        data = json.load(CACHE.open())
    else:
        data = fetch()
        CACHE.write_text(json.dumps(data, indent=2))

    issues = data["data"]["issues"]["nodes"]
    now = datetime.now(timezone.utc)
    for i in issues:
        i["_c"] = parse(i["createdAt"])
        i["_done"] = parse(i.get("completedAt"))
        i["_t"] = (i.get("state") or {}).get("type", "unknown")
        i["_s"] = (i.get("state") or {}).get("name", "Unknown")

    total = len(issues)
    completed = sum(1 for i in issues if i["_t"] == "completed")
    canceled = sum(1 for i in issues if i["_t"] == "canceled")
    open_ct = sum(1 for i in issues if i["_t"] not in ("completed", "canceled"))
    in_progress = sum(1 for i in issues if i["_t"] == "started")
    backlog = sum(1 for i in issues if i["_t"] == "backlog")

    weeks = []
    for w in range(11, -1, -1):
        end = now - timedelta(days=w * 7)
        start = end - timedelta(days=7)
        weeks.append({
            "label": end.strftime("%b %d"),
            "created": sum(1 for i in issues if i["_c"] and start < i["_c"] <= end),
            "closed": sum(1 for i in issues if i["_done"] and start < i["_done"] <= end),
        })
    burn_weeks = [b["closed"] for b in weeks[-8:]]
    burn_rate = round(sum(burn_weeks) / max(len(burn_weeks), 1), 1)
    weeks_to_clear = round(open_ct / burn_rate, 1) if burn_rate > 0 else None

    def since(field, d):
        c = now - timedelta(days=d)
        return sum(1 for i in issues if i[field] and i[field] >= c)

    state_counts = Counter(i["_s"] for i in issues)
    PRIO = {0: "None", 1: "Urgent", 2: "High", 3: "Medium", 4: "Low"}
    prio_counts = Counter(PRIO.get(i.get("priority", 0), "None") for i in issues)

    label_counts: Counter = Counter()
    for i in issues:
        for ln in (i.get("labels") or {}).get("nodes", []):
            label_counts[ln["name"]] += 1
    top_labels = label_counts.most_common(10)

    open_issues = [i for i in issues if i["_t"] not in ("completed", "canceled")]
    if open_issues:
        avg_age = round(sum((now - i["_c"]).days for i in open_issues) / len(open_issues), 1)
        oldest = max(open_issues, key=lambda i: now - i["_c"])
        oldest_age = (now - oldest["_c"]).days
    else:
        avg_age, oldest, oldest_age = 0, None, 0

    recent = sorted(issues, key=lambda i: i["_c"], reverse=True)[:15]
    recent_rows = [{
        "id": i["identifier"], "title": i["title"], "url": i["url"],
        "state": i["_s"], "state_type": i["_t"],
        "priority": PRIO.get(i.get("priority", 0), "None"),
        "created": i["_c"].strftime("%Y-%m-%d") if i["_c"] else "",
        "assignee": (i.get("assignee") or {}).get("name") or "\u2014",
    } for i in recent]

    stale = sorted(
        [i for i in open_issues if (now - i["_c"]).days > 14],
        key=lambda i: i["_c"],
    )
    stale_rows = [{
        "id": i["identifier"], "title": i["title"], "url": i["url"],
        "state": i["_s"], "age": (now - i["_c"]).days,
    } for i in stale[:10]]

    created_today, created_7d, created_30d = since("_c", 1), since("_c", 7), since("_c", 30)
    closed_today, closed_7d, closed_30d = since("_done", 1), since("_done", 7), since("_done", 30)
    net_30d = created_30d - closed_30d

    dashboard = {
        "generated": now.strftime("%Y-%m-%d %H:%M UTC"),
        "total": total, "open": open_ct, "completed": completed, "canceled": canceled,
        "in_progress": in_progress, "backlog": backlog,
        "completion_pct": round((completed / total) * 100, 1) if total else 0,
        "burn_rate": burn_rate, "weeks_to_clear": weeks_to_clear,
        "created_today": created_today, "created_7d": created_7d, "created_30d": created_30d,
        "closed_today": closed_today, "closed_7d": closed_7d, "closed_30d": closed_30d,
        "avg_age_days": avg_age, "oldest_age": oldest_age,
        "oldest_id": oldest["identifier"] if oldest else None,
        "oldest_url": oldest["url"] if oldest else None,
        "week_buckets": weeks,
        "state_counts": dict(state_counts), "prio_counts": dict(prio_counts),
        "top_labels": top_labels, "recent": recent_rows, "stale": stale_rows,
    }

    wtc_str = (
        f"~ {weeks_to_clear} weeks to clear at this rate"
        if weeks_to_clear else "no closures yet"
    )
    oldest_str = (
        f'<a href="{dashboard["oldest_url"]}" style="color:var(--accent);">'
        f'{dashboard["oldest_id"]} ({oldest_age}d)</a>'
        if oldest else "\u2014"
    )

    repl = {
        "__GENERATED__": dashboard["generated"], "__TOTAL__": str(total),
        "__OPEN__": str(open_ct), "__COMPLETED__": str(completed),
        "__CANCELED__": str(canceled), "__IN_PROGRESS__": str(in_progress),
        "__BACKLOG__": str(backlog),
        "__COMPLETION_PCT__": str(dashboard["completion_pct"]),
        "__BURN__": str(burn_rate), "__WTC__": wtc_str,
        "__AVG_AGE__": str(avg_age), "__OLDEST__": oldest_str,
        "__CREATED_TODAY__": str(created_today), "__CREATED_7D__": str(created_7d),
        "__CREATED_30D__": str(created_30d),
        "__CLOSED_TODAY__": str(closed_today), "__CLOSED_7D__": str(closed_7d),
        "__CLOSED_30D__": str(closed_30d),
        "__NET_30D__": f"+{net_30d}" if net_30d >= 0 else str(net_30d),
        "__DASHBOARD_JSON__": json.dumps(dashboard, default=str),
    }
    html = TEMPLATE.read_text()
    for k, v in repl.items():
        html = html.replace(k, v)
    OUT.write_text(html)
    print(f"wrote {OUT} ({len(html):,} bytes)")
    print(f"  total={total} open={open_ct} completed={completed} canceled={canceled}")
    print(f"  burn={burn_rate}/wk avg_open_age={avg_age}d")


if __name__ == "__main__":
    build()
