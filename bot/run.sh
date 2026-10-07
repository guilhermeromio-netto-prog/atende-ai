#!/usr/bin/env bash
# Mantém o bot rodando: reinicia se cair. Uso: TELEGRAM_BOT_TOKEN=... nohup bot/run.sh &
# O token vem só do ambiente; nada é gravado em disco.
cd "$(dirname "$0")"
mkdir -p data
exec 9>data/run.lock
flock -n 9 || { echo "run.sh já está rodando"; exit 1; }
echo $$ > data/run.pid
if [ -z "$(printf %s "${TELEGRAM_BOT_TOKEN:-}" | tr -d '[:space:]')" ]; then echo "TELEGRAM_BOT_TOKEN ausente" >> data/bot.log; exit 2; fi
while true; do
  echo "$(date '+%F %T') iniciando bot" >> data/bot.log
  python3 -u atende_bot.py >> data/bot.log 2>&1
  echo "$(date '+%F %T') bot saiu (código $?); reiniciando em 5 s" >> data/bot.log
  sleep 5
done
