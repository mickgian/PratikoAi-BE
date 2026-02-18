#!/bin/bash
set -e

# Print initial environment values (before loading .env)
echo "Starting with these environment variables:"
echo "APP_ENV: ${APP_ENV:-development}"
if [[ -n "$POSTGRES_URL" && "$POSTGRES_URL" == *"@"* ]]; then
    INITIAL_DB_DISPLAY=$(echo "$POSTGRES_URL" | sed 's/.*@/@/')
    echo "Initial Database URL: *********$INITIAL_DB_DISPLAY"
else
    echo "Initial Database URL: ${POSTGRES_URL:-Not set}"
fi

# Load environment variables from the appropriate .env file
if [ -f ".env.${APP_ENV}" ]; then
    echo "Loading environment from .env.${APP_ENV}"
    while IFS= read -r line || [[ -n "$line" ]]; do
        # Skip comments and empty lines
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "$line" ]] && continue

        # Extract the key
        key=$(echo "$line" | cut -d '=' -f 1)

        # Only set if not already set in environment
        if [[ -z "${!key}" ]]; then
            export "$line"
        else
            echo "Keeping existing value for $key"
        fi
    done <".env.${APP_ENV}"
elif [ -f ".env" ]; then
    echo "Loading environment from .env"
    while IFS= read -r line || [[ -n "$line" ]]; do
        # Skip comments and empty lines
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "$line" ]] && continue

        # Extract the key
        key=$(echo "$line" | cut -d '=' -f 1)

        # Only set if not already set in environment
        if [[ -z "${!key}" ]]; then
            export "$line"
        else
            echo "Keeping existing value for $key"
        fi
    done <".env"
else
    echo "Warning: No .env file found. Using system environment variables."
fi

# Check required sensitive environment variables
required_vars=("JWT_SECRET_KEY" "LLM_API_KEY")
if [ "$APP_ENV" != "development" ]; then
    required_vars+=("POSTGRES_URL")
fi
missing_vars=()

for var in "${required_vars[@]}"; do
    if [[ -z "${!var}" ]]; then
        missing_vars+=("$var")
    fi
done

if [[ ${#missing_vars[@]} -gt 0 ]]; then
    echo "ERROR: The following required environment variables are missing:"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    echo "Please provide these variables through environment or .env files."
    exit 1
fi

# Print final environment info
echo -e "\nFinal environment configuration:"
echo "Environment: ${APP_ENV:-development}"

# Show only the part after @ for database URL (for security)
if [[ -n "$POSTGRES_URL" && "$POSTGRES_URL" == *"@"* ]]; then
    DB_DISPLAY=$(echo "$POSTGRES_URL" | sed 's/.*@/@/')
    echo "Database URL: *********$DB_DISPLAY"
else
    echo "Database URL: ${POSTGRES_URL:-Not set}"
fi

echo "LLM Model: ${LLM_MODEL:-Not set}"
echo "Debug Mode: ${DEBUG:-false}"

# Wait for database to be ready before running migrations
if [ "$APP_ENV" != "development" ]; then
    echo "Waiting for database..."
    # Extract host and port from POSTGRES_URL
    DB_HOST=$(echo "$POSTGRES_URL" | sed -n 's|.*@\([^:/]*\).*|\1|p')
    DB_PORT=$(echo "$POSTGRES_URL" | sed -n 's|.*:\([0-9]*\)/.*|\1|p')
    DB_PORT=${DB_PORT:-5432}

    for i in $(seq 1 15); do
        if pg_isready -h "$DB_HOST" -p "$DB_PORT" -q 2>/dev/null; then
            echo "Database is ready."
            break
        fi
        if [ "$i" -eq 15 ]; then
            echo "ERROR: Database not ready after 30s"
            exit 1
        fi
        echo "Database not ready, retrying in 2s... ($i/15)"
        sleep 2
    done

    echo "Running database migrations..."
    /app/.venv/bin/alembic upgrade head
    echo "Migrations complete."
fi

# Execute the CMD
exec "$@"
