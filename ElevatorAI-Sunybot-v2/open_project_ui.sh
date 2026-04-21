#!/usr/bin/env bash
set -e

cd ~/elevator_ai_project
./start_all.sh

sleep 5

xdg-open http://127.0.0.1:8000 >/dev/null 2>&1 &

