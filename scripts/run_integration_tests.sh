#!/bin/bash
# DB/engine-backed checks in throwaway containers on a private Docker network: a fresh
# Postgres 16 and the Rust engine image. Never touches the compose stack, its volumes, or any
# real data, and makes no exchange or LLM calls. Everything it starts is removed on exit.
# Run from the repo root:  bash scripts/run_integration_tests.sh
set -euo pipefail
cd "$(dirname "$0")/.."

NET=btc-it-net PG=btc-it-pg ENGINE=btc-it-engine
DB_URL="postgresql+asyncpg://test:test@$PG:5432/autotrade_test"
# Throwaway secrets, generated per run; the JWT key is 32 bytes (HS256 minimum).
JWT=$(openssl rand -hex 32)
FERNET=$(openssl rand -base64 32 | tr '+/' '-_')

cleanup() { docker rm -f "$PG" "$ENGINE" >/dev/null 2>&1 || true; docker network rm "$NET" >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup

docker build -q -t bottradingcrypto-backend ./backend >/dev/null
docker build -q -t bottradingcrypto-engine ./engine >/dev/null
docker network create "$NET" >/dev/null
docker run -d --name "$ENGINE" --network "$NET" bottradingcrypto-engine >/dev/null

backend() {  # backend <extra docker args...> -- <command...>
  local args=()
  while [ "$1" != "--" ]; do args+=("$1"); shift; done; shift
  docker run --rm --network "$NET" -v "$PWD/backend:/app" -v "$PWD/.agents:/app/.agents:ro" -w /app \
    -e DATABASE_URL="$DB_URL" -e JWT_SECRET_KEY="$JWT" -e FIELD_ENCRYPTION_KEY="$FERNET" \
    ${args[@]+"${args[@]}"} bottradingcrypto-backend "$@"  # empty-array-safe on macOS bash 3.2
}

fresh_db() {  # each suite gets an empty, freshly migrated database
  docker rm -f "$PG" >/dev/null 2>&1 || true
  docker run -d --name "$PG" --network "$NET" -e POSTGRES_DB=autotrade_test \
    -e POSTGRES_USER=test -e POSTGRES_PASSWORD=test postgres:16-alpine >/dev/null
  # pg_isready can pass during the image's init restart, so wait for a real query instead.
  for _ in $(seq 1 60); do
    docker exec "$PG" psql -U test -d autotrade_test -c "SELECT 1" >/dev/null 2>&1 && break
    sleep 1
  done
  local out
  out=$(backend -- alembic upgrade head 2>&1) || { echo "migration failed:"; echo "$out"; return 1; }
}

run() {  # run <label> <extra docker args...> -- <command...>
  # Quiet on success (the suites log expected errors, e.g. the injected DB failure); full output on failure.
  local label=$1 out; shift
  printf '== %-45s ' "$label"
  if out=$(backend "$@" 2>&1); then
    echo "${out##*$'\n'}"
  else
    echo "FAILED"; echo "$out" | tail -40; return 1
  fi
}

fresh_db
tables=$(docker exec "$PG" psql -U test -d autotrade_test -tAc \
  "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name <> 'alembic_version'")
echo "== migrations 001-005 on an empty DB: $tables domain tables"
[ "$tables" = "20" ]

run "http (APP_ENV=development)" -e APP_ENV=development -- python -m src.api.test_http
fresh_db
run "http (APP_ENV=production, Secure cookie)" -e APP_ENV=production -- python -m src.api.test_http
fresh_db
run "e2e, Python gate only" -- python -m src.risk.test_engine_e2e
fresh_db
run "e2e, Rust engine up" -e ENGINE_URL="http://$ENGINE:8080" -e ENGINE_TIMEOUT_MS=2000 -e E2E_ENGINE_MODE=up \
  -- python -m src.risk.test_engine_e2e
fresh_db
run "e2e, Rust engine down (fail-closed)" -e ENGINE_URL="http://$ENGINE:9" -e E2E_ENGINE_MODE=down \
  -- python -m src.risk.test_engine_e2e
fresh_db
run "copy-trade chain (synthetic, mocked RPC/DEX)" -- python -m src.agents.test_copy_trade_chain
run "parity Python vs Rust image" -e PARITY_ENGINE_URL="http://$ENGINE:8080" -- python -m src.risk.test_parity
echo "all integration checks passed"
