#!/usr/bin/env bash
set -e

NEX_DIR="$(cd "$(dirname "$0")" && pwd)"
FREELM_PORT="${FREELM_PORT:-3000}"

cleanup() {
  echo ""
  echo "Deteniendo FreeLLM..."
  if [ -n "$FREELM_PID" ] && kill -0 "$FREELM_PID" 2>/dev/null; then
    kill "$FREELM_PID" 2>/dev/null
    wait "$FREELM_PID" 2>/dev/null
  fi
  exit 0
}
trap cleanup SIGINT SIGTERM

# Matar instancia previa si existe
if lsof -ti :"$FREELM_PORT" > /dev/null 2>&1; then
  echo "Cerrando FreeLLM anterior..."
  kill $(lsof -ti :"$FREELM_PORT") 2>/dev/null
  sleep 0.5
fi

echo "Iniciando FreeLLM en http://127.0.0.1:$FREELM_PORT ..."
npx --prefix "$NEX_DIR/frontend" freellm --port "$FREELM_PORT" --no-open &
FREELM_PID=$!

# Esperar a que responda
for i in $(seq 1 30); do
  if curl -s "http://127.0.0.1:$FREELM_PORT/v1/models" > /dev/null 2>&1; then
    echo "FreeLLM listo en http://127.0.0.1:$FREELM_PORT"
    break
  fi
  sleep 0.5
done

wait $FREELM_PID
