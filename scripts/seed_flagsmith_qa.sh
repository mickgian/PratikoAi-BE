#!/bin/bash
# =============================================================================
# PratikoAI Flagsmith QA Seed Script
# =============================================================================
# Automates Flagsmith setup for QA: superuser, org, project, feature flags.
# All steps are idempotent — safe to re-run on every deploy.
#
# Usage:
#   bash scripts/seed_flagsmith_qa.sh
#
# Required env vars:
#   FLAGSMITH_ADMIN_EMAIL    - Superuser email
#   FLAGSMITH_ADMIN_PASSWORD - Superuser password
#
# Expects to run from /opt/pratikoai on the QA server.
# =============================================================================

set -euo pipefail

# --- Config ---
FLAGSMITH_ADMIN_EMAIL="${FLAGSMITH_ADMIN_EMAIL:?FLAGSMITH_ADMIN_EMAIL required}"
FLAGSMITH_ADMIN_PASSWORD="${FLAGSMITH_ADMIN_PASSWORD:?FLAGSMITH_ADMIN_PASSWORD required}"
FLAGSMITH_URL="http://flagsmith:8000"
ORG_NAME="PratikoAI"
PROJECT_NAME="PratikoAI QA"

DC="${DC:-docker compose --env-file .env.qa -f docker-compose.yml -f docker-compose.qa.yml}"

# Helper: run curl inside the app container (Flagsmith is only on Docker network)
api() {
    $DC exec -T app curl -sf --max-time 15 "$@"
}

# Helper: parse JSON with python3 (same pattern as smoke_test.sh)
pyjson() {
    python3 -c "import sys,json; data=json.load(sys.stdin); $1"
}

echo "=== Flagsmith QA Seed ==="
echo "Time: $(date -u)"
echo ""

# --- [0/7] Wait for Flagsmith health ---
echo "[0/7] Waiting for Flagsmith to be healthy..."
for i in $(seq 1 30); do
    if $DC exec -T app curl -sf --max-time 5 "${FLAGSMITH_URL}/health" > /dev/null 2>&1; then
        echo "  Flagsmith healthy!"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "  ERROR: Flagsmith not healthy after 150s"
        exit 1
    fi
    echo "  Waiting... (attempt $i/30)"
    sleep 5
done

# --- [1/7] Create superuser ---
echo "[1/7] Creating Flagsmith superuser..."
$DC exec -T \
    -e DJANGO_SUPERUSER_EMAIL="$FLAGSMITH_ADMIN_EMAIL" \
    -e DJANGO_SUPERUSER_PASSWORD="$FLAGSMITH_ADMIN_PASSWORD" \
    flagsmith python manage.py createsuperuser --noinput 2>&1 \
    | grep -v "^$" || true
echo "  Superuser ready (created or already exists)"

# --- [2/7] Login via API ---
echo "[2/7] Logging in..."
LOGIN_RESPONSE=$(api -X POST "${FLAGSMITH_URL}/api/v1/auth/login/" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${FLAGSMITH_ADMIN_EMAIL}\",\"password\":\"${FLAGSMITH_ADMIN_PASSWORD}\"}")
TOKEN=$(echo "$LOGIN_RESPONSE" | pyjson "print(data['key'])")
if [ -z "$TOKEN" ]; then
    echo "  ERROR: Failed to get auth token"
    exit 1
fi
echo "  Logged in (token obtained)"

AUTH_HEADER="Authorization: Token ${TOKEN}"

# --- [3/7] Get or create organisation ---
echo "[3/7] Getting or creating organisation '${ORG_NAME}'..."
ORGS_RESPONSE=$(api -H "$AUTH_HEADER" "${FLAGSMITH_URL}/api/v1/organisations/")
ORG_ID=$(echo "$ORGS_RESPONSE" | pyjson "
results = data if isinstance(data, list) else data.get('results', [])
orgs = [o for o in results if o['name'] == '${ORG_NAME}']
print(orgs[0]['id'] if orgs else '')
")

if [ -z "$ORG_ID" ]; then
    CREATE_ORG=$(api -X POST -H "$AUTH_HEADER" \
        -H "Content-Type: application/json" \
        -d "{\"name\":\"${ORG_NAME}\"}" \
        "${FLAGSMITH_URL}/api/v1/organisations/")
    ORG_ID=$(echo "$CREATE_ORG" | pyjson "print(data['id'])")
    echo "  Created org: ${ORG_NAME} (id=${ORG_ID})"
else
    echo "  Exists: ${ORG_NAME} (id=${ORG_ID})"
fi

# --- [4/7] Get or create project ---
echo "[4/7] Getting or creating project '${PROJECT_NAME}'..."
PROJECTS_RESPONSE=$(api -H "$AUTH_HEADER" "${FLAGSMITH_URL}/api/v1/projects/")
PROJECT_ID=$(echo "$PROJECTS_RESPONSE" | pyjson "
projects = data if isinstance(data, list) else data.get('results', [])
ps = [p for p in projects if p['name'] == '${PROJECT_NAME}']
print(ps[0]['id'] if ps else '')
")

if [ -z "$PROJECT_ID" ]; then
    CREATE_PROJECT=$(api -X POST -H "$AUTH_HEADER" \
        -H "Content-Type: application/json" \
        -d "{\"name\":\"${PROJECT_NAME}\",\"organisation\":${ORG_ID}}" \
        "${FLAGSMITH_URL}/api/v1/projects/")
    PROJECT_ID=$(echo "$CREATE_PROJECT" | pyjson "print(data['id'])")
    echo "  Created project: ${PROJECT_NAME} (id=${PROJECT_ID})"
else
    echo "  Exists: ${PROJECT_NAME} (id=${PROJECT_ID})"
fi

# --- [5/7] Get environment server-side key ---
echo "[5/7] Getting environment server-side key..."
ENVS_RESPONSE=$(api -H "$AUTH_HEADER" "${FLAGSMITH_URL}/api/v1/environments/?project=${PROJECT_ID}")
SERVER_KEY=$(echo "$ENVS_RESPONSE" | pyjson "
envs = data if isinstance(data, list) else data.get('results', [])
dev = [e for e in envs if e['name'] == 'Development']
print(dev[0]['api_key'] if dev else '')
")

if [ -z "$SERVER_KEY" ]; then
    echo "  ERROR: No 'Development' environment found"
    exit 1
fi
echo "  Server key: ${SERVER_KEY:0:8}..."

# --- [6/7] Seed feature flags ---
echo "[6/7] Seeding feature flags..."

FLAGS_JSON=$(cat <<'FLAGSEOF'
[
  {"name": "WEB_VERIFICATION_ENABLED", "default_enabled": true, "initial_value": ""},
  {"name": "CACHE_ENABLED", "default_enabled": true, "initial_value": ""},
  {"name": "OCR_ENABLED", "default_enabled": true, "initial_value": ""},
  {"name": "PRODUCTION_LLM_MODEL", "default_enabled": true, "initial_value": "mistral-large-latest"},
  {"name": "DEFAULT_LLM_TEMPERATURE", "default_enabled": true, "initial_value": "0.2"},
  {"name": "HYBRID_WEIGHT_FTS", "default_enabled": true, "initial_value": "0.45"},
  {"name": "HYBRID_WEIGHT_VEC", "default_enabled": true, "initial_value": "0.30"},
  {"name": "HYBRID_WEIGHT_RECENCY", "default_enabled": true, "initial_value": "0.10"},
  {"name": "HYBRID_WEIGHT_QUALITY", "default_enabled": true, "initial_value": "0.10"},
  {"name": "HYBRID_WEIGHT_SOURCE", "default_enabled": true, "initial_value": "0.05"},
  {"name": "CONTEXT_TOP_K", "default_enabled": true, "initial_value": "25"}
]
FLAGSEOF
)

FLAG_COUNT=$(echo "$FLAGS_JSON" | pyjson "print(len(data))")
CREATED=0
EXISTED=0

for idx in $(seq 0 $((FLAG_COUNT - 1))); do
    FLAG_NAME=$(echo "$FLAGS_JSON" | pyjson "print(data[$idx]['name'])")
    FLAG_ENABLED=$(echo "$FLAGS_JSON" | pyjson "print(str(data[$idx]['default_enabled']).lower())")
    FLAG_VALUE=$(echo "$FLAGS_JSON" | pyjson "print(data[$idx]['initial_value'])")

    # Check if flag already exists
    EXISTING=$(api -H "$AUTH_HEADER" \
        "${FLAGSMITH_URL}/api/v1/projects/${PROJECT_ID}/features/?search=${FLAG_NAME}" 2>/dev/null || echo "")

    FLAG_EXISTS=$(echo "$EXISTING" | pyjson "
results = data if isinstance(data, list) else data.get('results', [])
matches = [f for f in results if f['name'] == '${FLAG_NAME}']
print('yes' if matches else 'no')
" 2>/dev/null || echo "no")

    if [ "$FLAG_EXISTS" = "yes" ]; then
        echo "  Exists: ${FLAG_NAME}"
        EXISTED=$((EXISTED + 1))
    else
        api -X POST -H "$AUTH_HEADER" \
            -H "Content-Type: application/json" \
            -d "{\"name\":\"${FLAG_NAME}\",\"default_enabled\":${FLAG_ENABLED},\"initial_value\":\"${FLAG_VALUE}\",\"project\":${PROJECT_ID}}" \
            "${FLAGSMITH_URL}/api/v1/projects/${PROJECT_ID}/features/" > /dev/null
        echo "  Created: ${FLAG_NAME}"
        CREATED=$((CREATED + 1))
    fi
done

echo "  Flags: ${CREATED} created, ${EXISTED} already existed"

# --- [7/7] Update .env.qa ---
echo "[7/7] Updating .env.qa with server key..."
ENV_FILE=".env.qa"

if [ -f "$ENV_FILE" ]; then
    if grep -q "^FLAGSMITH_SERVER_KEY=" "$ENV_FILE"; then
        CURRENT_KEY=$(grep "^FLAGSMITH_SERVER_KEY=" "$ENV_FILE" | cut -d'=' -f2)
        if [ "$CURRENT_KEY" = "$SERVER_KEY" ]; then
            echo "  .env.qa already has correct key"
        else
            sed -i "s|^FLAGSMITH_SERVER_KEY=.*|FLAGSMITH_SERVER_KEY=${SERVER_KEY}|" "$ENV_FILE"
            echo "  Updated FLAGSMITH_SERVER_KEY in .env.qa"
        fi
    else
        echo "FLAGSMITH_SERVER_KEY=${SERVER_KEY}" >> "$ENV_FILE"
        echo "  Appended FLAGSMITH_SERVER_KEY to .env.qa"
    fi
else
    echo "  WARNING: ${ENV_FILE} not found, skipping"
fi

echo ""
echo "=== Flagsmith QA Seed Complete ==="
