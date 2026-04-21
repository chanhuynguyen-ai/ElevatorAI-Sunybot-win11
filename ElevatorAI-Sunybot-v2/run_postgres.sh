#!/usr/bin/env bash
set -e

sudo -u postgres /usr/local/pgsql16/bin/pg_ctl \
 -D /usr/local/pgsql16/data \
 -l /usr/local/pgsql16/data/logfile start || true

echo "[INFO] PostgreSQL status:"
sudo -u postgres /usr/local/pgsql16/bin/pg_ctl \
 -D /usr/local/pgsql16/data status || true

