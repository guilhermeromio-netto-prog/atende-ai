#!/usr/bin/env bash
# Túnel rápido do Cloudflare (sem conta) para a API de leitura em 127.0.0.1:8787.
# A URL https://*.trycloudflare.com muda a cada reinício; fica em data/tunnel_url.txt.
cd "$(dirname "$0")"
mkdir -p data
CF="${CLOUDFLARED:-/workspace/tools/cloudflared}"
exec 8>data/tunnel.lock
flock -n 8 || { echo "tunnel.sh já está rodando"; exit 1; }
echo $$ > data/tunnel.pid
while true; do
  : > data/tunnel_url.txt
  echo "$(date '+%F %T') iniciando túnel" >> data/tunnel.log
  "$CF" tunnel --no-autoupdate --url http://127.0.0.1:8787 2>&1 | while IFS= read -r linha; do
    echo "$linha" >> data/tunnel.log
    url=$(printf '%s' "$linha" | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' | head -1)
    [ -n "$url" ] && printf '%s\n' "$url" > data/tunnel_url.txt
  done
  echo "$(date '+%F %T') túnel caiu; reiniciando em 10 s" >> data/tunnel.log
  sleep 10
done
