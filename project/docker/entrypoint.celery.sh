#!/bin/bash
# =============================================================================
# PPT Master - Celery Worker Entrypoint Script
# Waits for dependencies, then starts Celery worker
# =============================================================================

set -euo pipefail

# Colors for output (only when TTY is available)
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
fi

# Logging functions
log_info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# =============================================================================
# Configuration
# =============================================================================

# Timeouts (seconds)
DB_WAIT_TIMEOUT=${DB_WAIT_TIMEOUT:-60}
REDIS_WAIT_TIMEOUT=${REDIS_WAIT_TIMEOUT:-30}

# Connection settings
DB_HOST=${DB_HOST:-db}
DB_PORT=${DB_PORT:-5432}
REDIS_HOST=${REDIS_HOST:-redis}
REDIS_PORT=${REDIS_PORT:-6379}

# Skip flags
SKIP_DB_WAIT=${SKIP_DB_WAIT:-false}
SKIP_REDIS_WAIT=${SKIP_REDIS_WAIT:-false}

# =============================================================================
# Wait for service to be ready (TCP connection check)
# =============================================================================

wait_for_service() {
    local name="$1"
    local host="$2"
    local port="$3"
    local timeout="$4"
    local start_time=$(date +%s)

    log_info "Waiting for ${name} at ${host}:${port}..."

    while ! nc -z "${host}" "${port}" 2>/dev/null; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))

        if [ ${elapsed} -ge ${timeout} ]; then
            log_error "Timeout waiting for ${name} after ${timeout} seconds"
            exit 1
        fi

        echo -n "."
        sleep 1
    done

    # Wait a moment for service to fully initialize
    sleep 2
    echo
    log_ok "${name} is ready! (${host}:${port})"
}

# =============================================================================
# Wait for Redis to be ready (with PING check)
# =============================================================================

wait_for_redis() {
    local host="$1"
    local port="$2"
    local timeout="$3"
    local start_time=$(date +%s)

    log_info "Waiting for Redis at ${host}:${port} (with PING check)..."

    while true; do
        # Try to PING redis
        if redis-cli -h "${host}" -p "${port}" ping 2>/dev/null | grep -q "PONG"; then
            break
        fi

        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))

        if [ ${elapsed} -ge ${timeout} ]; then
            log_error "Timeout waiting for Redis PONG response after ${timeout} seconds"
            exit 1
        fi

        echo -n "."
        sleep 1
    done

    echo
    log_ok "Redis is ready and responding to PING! (${host}:${port})"
}

# =============================================================================
# Check database connectivity using Python (since Celery needs the DB)
# =============================================================================

check_database() {
    local db_url="${DATABASE_URL}"

    log_info "Checking database connectivity..."

    python3 -c "
import asyncio
import sys

try:
    from sqlalchemy.ext.asyncio import create_async_engine
    
    async def check():
        engine = create_async_engine('${db_url}', echo=False)
        async with engine.connect() as conn:
            result = await conn.execute('SELECT 1')
            await conn.commit()
        await engine.dispose()
        print('Database connection OK')
    
    asyncio.run(check())
    sys.exit(0)
except Exception as e:
    print(f'Database check failed: {e}', file=sys.stderr)
    sys.exit(1)
" || {
        log_warn "Database connectivity check via Python failed, but continuing..."
        return 0
    }
}

# =============================================================================
# Main
# =============================================================================

main() {
    echo "========================================"
    echo "  PPT Master - Celery Worker Entrypoint"
    echo "========================================"

    # -------------------------------------------------------------------------
    # Wait for dependencies
    # -------------------------------------------------------------------------

    if [ "${SKIP_DB_WAIT}" != "true" ]; then
        wait_for_service "PostgreSQL" "${DB_HOST}" "${DB_PORT}" "${DB_WAIT_TIMEOUT}"
    else
        log_warn "Skipping database wait (SKIP_DB_WAIT=true)"
    fi

    if [ "${SKIP_REDIS_WAIT}" != "true" ]; then
        wait_for_service "Redis" "${REDIS_HOST}" "${REDIS_PORT}" "${REDIS_WAIT_TIMEOUT}"
        # Also do a PING check for Redis
        if command -v redis-cli &>/dev/null; then
            wait_for_redis "${REDIS_HOST}" "${REDIS_PORT}" "${REDIS_WAIT_TIMEOUT}"
        fi
    else
        log_warn "Skipping Redis wait (SKIP_REDIS_WAIT=true)"
    fi

    # Optional: check database connectivity
    check_database || true

    # -------------------------------------------------------------------------
    # Start Celery worker
    # -------------------------------------------------------------------------

    echo "========================================"
    log_ok "Dependencies ready! Starting Celery worker..."
    echo "========================================"
    echo "Command: $*"
    echo ""

    # Clean up any stale PID files
    rm -f /tmp/celery*.pid

    # Execute the passed command
    exec "$@"
}

# Run main function with all arguments
main "$@"
