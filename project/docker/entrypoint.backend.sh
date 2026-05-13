#!/bin/bash
# =============================================================================
# PPT Master - Backend Entrypoint Script
# Waits for dependencies, runs migrations, then starts the application
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
MINIO_WAIT_TIMEOUT=${MINIO_WAIT_TIMEOUT:-30}

# Connection settings
DB_HOST=${DB_HOST:-db}
DB_PORT=${DB_PORT:-5432}
REDIS_HOST=${REDIS_HOST:-redis}
REDIS_PORT=${REDIS_PORT:-6379}
MINIO_HOST=${MINIO_HOST:-minio}
MINIO_PORT=${MINIO_PORT:-9000}

# Skip flags
SKIP_MIGRATIONS=${SKIP_MIGRATIONS:-false}
SKIP_DB_WAIT=${SKIP_DB_WAIT:-false}
SKIP_REDIS_WAIT=${SKIP_REDIS_WAIT:-false}

# =============================================================================
# Wait for service to be ready
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
# Wait for MinIO to be ready
# =============================================================================

wait_for_minio() {
    local name="$1"
    local host="$2"
    local port="$3"
    local timeout="$4"
    local start_time=$(date +%s)

    log_info "Waiting for ${name} at ${host}:${port}..."

    while ! curl -sf "http://${host}:${port}/minio/health/live" >/dev/null 2>&1; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))

        if [ ${elapsed} -ge ${timeout} ]; then
            log_warn "Timeout waiting for ${name} after ${timeout} seconds (continuing anyway)"
            return 0
        fi

        echo -n "."
        sleep 2
    done

    echo
    log_ok "${name} is ready! (${host}:${port})"
}

# =============================================================================
# Run database migrations
# =============================================================================

run_migrations() {
    log_info "Running database migrations..."

    # Check if alembic is available
    if command -v alembic &>/dev/null; then
        cd "${APP_HOME}"

        # Check if migrations directory exists
        if [ -d "alembic" ] || [ -d "migrations" ]; then
            log_info "Executing Alembic upgrade..."
            alembic upgrade head
            log_ok "Migrations completed successfully!"
        else
            log_warn "No migrations directory found. Skipping migrations."
            log_info "If this is the first run, create migrations with: alembic init migrations"
        fi
    else
        log_warn "Alembic not found in PATH. Skipping migrations."
    fi
}

# =============================================================================
# Create MinIO bucket if it doesn't exist
# =============================================================================

create_minio_bucket() {
    local bucket_name=${MINIO_BUCKET:-pptmaster}
    local minio_url="http://${MINIO_HOST}:${MINIO_PORT}"
    local access_key=${MINIO_ACCESS_KEY:-minioadmin}
    local secret_key=${MINIO_SECRET_KEY:-minioadmin}

    log_info "Checking MinIO bucket '${bucket_name}'..."

    # Use mc alias to configure and check/create bucket
    if command -v mc &>/dev/null; then
        mc alias set local "${minio_url}" "${access_key}" "${secret_key}" --insecure 2>/dev/null || true
        if ! mc ls local/${bucket_name} >/dev/null 2>&1; then
            log_info "Creating MinIO bucket '${bucket_name}'..."
            mc mb local/${bucket_name} 2>/dev/null || log_warn "Failed to create bucket (may already exist)"
        else
            log_ok "MinIO bucket '${bucket_name}' already exists"
        fi
    else
        # Fallback using curl
        log_info "mc not available, attempting bucket creation via API..."
        # Note: bucket creation via curl requires proper S3 signature
        log_warn "Skipping automatic bucket creation. Ensure bucket '${bucket_name}' exists."
    fi
}

# =============================================================================
# Main
# =============================================================================

main() {
    echo "========================================"
    echo "  PPT Master - Backend Entrypoint"
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
    else
        log_warn "Skipping Redis wait (SKIP_REDIS_WAIT=true)"
    fi

    # Wait for MinIO (optional, don't fail if not available)
    wait_for_minio "MinIO" "${MINIO_HOST}" "${MINIO_PORT}" "${MINIO_WAIT_TIMEOUT}" || true

    # -------------------------------------------------------------------------
    # Run migrations
    # -------------------------------------------------------------------------

    if [ "${SKIP_MIGRATIONS}" != "true" ]; then
        run_migrations
    else
        log_warn "Skipping migrations (SKIP_MIGRATIONS=true)"
    fi

    # -------------------------------------------------------------------------
    # Setup MinIO bucket
    # -------------------------------------------------------------------------

    if [ "${SKIP_MINIO_SETUP:-false}" != "true" ]; then
        create_minio_bucket || true
    fi

    # -------------------------------------------------------------------------
    # Start application
    # -------------------------------------------------------------------------

    echo "========================================"
    log_ok "Setup complete! Starting application..."
    echo "========================================"
    echo "Command: $*"
    echo ""

    # Execute the passed command (or default)
    exec "$@"
}

# Run main function with all arguments
main "$@"
