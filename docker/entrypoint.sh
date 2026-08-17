#!/bin/sh
# Build once at startup, then let busybox crond refresh every 30 minutes.
# Cron output goes to /proc/1/fd/1 so it lands in `docker logs`.
set -eu

echo "*/30 * * * * cd /app && python3 src/build.py >> /proc/1/fd/1 2>&1" | crontab -

cd /app && python3 src/build.py || echo "WARN: initial build failed; crond will retry" >&2

exec crond -f -l 8
