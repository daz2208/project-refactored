#!/bin/bash
# =============================================================================
# SyncBoard 3.0 Knowledge Bank - Database Restore Script (Phase 6)
# =============================================================================
# Restores database from backup file
# Usage: ./scripts/restore.sh <backup_file>
# =============================================================================

set -e  # Exit on error

# Check arguments
if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file>"
    echo ""
    echo "Example:"
    echo "  $0 backups/syncboard_backup_20231113_120000.sql.dump"
    echo "  $0 backups/syncboard_backup_20231113_120000.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ ERROR: Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Extract database connection details from DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERROR: DATABASE_URL not set"
    exit 1
fi

# Parse DATABASE_URL
DB_USER=$(echo $DATABASE_URL | sed -n 's/.*:\/\/\([^:]*\):.*/\1/p')
DB_PASS=$(echo $DATABASE_URL | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p')
DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
DB_NAME=$(echo $DATABASE_URL | sed -n 's/.*\/\([^?]*\).*/\1/p')

echo "⚠️  WARNING: This will overwrite the current database!"
echo "   Database: $DB_NAME"
echo "   Host: $DB_HOST:$DB_PORT"
echo "   Backup file: $BACKUP_FILE"
echo ""
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "❌ Restore cancelled"
    exit 0
fi

export PGPASSWORD="$DB_PASS"

echo "🔄 Starting restore..."

# Check file extension and restore accordingly
if [[ "$BACKUP_FILE" == *.dump ]]; then
    # Custom format backup
    echo "   Using pg_restore (custom format)..."
    pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        --clean --if-exists \
        "$BACKUP_FILE"

elif [[ "$BACKUP_FILE" == *.sql.gz ]]; then
    # Compressed SQL backup
    echo "   Using gunzip | psql (SQL format)..."
    gunzip -c "$BACKUP_FILE" | psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME"

elif [[ "$BACKUP_FILE" == *.sql ]]; then
    # Plain SQL backup
    echo "   Using psql (SQL format)..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" < "$BACKUP_FILE"

else
    echo "❌ ERROR: Unsupported backup file format"
    echo "   Supported: .dump, .sql, .sql.gz"
    exit 1
fi

echo "✅ Restore completed successfully!"
echo "   Database: $DB_NAME"
