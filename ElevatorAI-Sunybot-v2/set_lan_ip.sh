#!/usr/bin/env bash
set -e

if [ -z "$1" ]; then
echo "Usage: ./set_lan_ip.sh <WIN11_IP>"
exit 1
fi

IP="$1"
ENV_FILE="$HOME/elevator_ai_project/.env.llm.lan"

sed -i "s|^export OLLAMA_HOST=.*|export OLLAMA_HOST=http://$IP:11434|" "$ENV_FILE"

echo "[INFO] Updated OLLAMA_HOST to http://$IP:11434"
grep '^export OLLAMA_HOST=' "$ENV_FILE"



