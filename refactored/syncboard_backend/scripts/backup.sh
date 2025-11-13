#!/bin/bash
# =============================================================================
# SyncBoard 3.0 Knowledge Bank - Database Backup Script (Phase 6)
# =============================================================================
# Creates timestamped backup of PostgreSQL database
# Usage: ./scripts/backup.sh [output_directory]
# =============================================================================

set -e  # Exit on error

# Configuration
BACKUP_DIR="${1:-./backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="syncboard_backup_${TIMESTAMP}.sql"

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Extract database connection details from DATABASE_URL
# Format: postgresql://user:password@host:port/database
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

echo "🔄 Starting backup..."
echo "   Database: $DB_NAME"
echo "   Host: $DB_HOST:$DB_PORT"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Run pg_dump
export PGPASSWORD="$DB_PASS"
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --format=custom \
    --file="${BACKUP_DIR}/${BACKUP_FILE}.dump"

# Also create SQL version for easier inspection
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --file="${BACKUP_DIR}/${BACKUP_FILE}"

# Compress SQL file
gzip "${BACKUP_DIR}/${BACKUP_FILE}"

echo "✅ Backup completed successfully!"
echo "   Custom format: ${BACKUP_DIR}/${BACKUP_FILE}.dump"
echo "   SQL (gzipped): ${BACKUP_DIR}/${BACKUP_FILE}.gz"

# Calculate sizes
DUMP_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_FILE}.dump" | cut -f1)
SQL_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_FILE}.gz" | cut -f1)

echo "   Dump size: $DUMP_SIZE"
echo "   SQL size: $SQL_SIZE"

# Keep only last 7 backups (optional cleanup)
echo "🗑️  Cleaning up old backups (keeping last 7)..."
cd "$BACKUP_DIR"
ls -t syncboard_backup_*.dump | tail -n +8 | xargs -r rm
ls -t syncboard_backup_*.sql.gz | tail -n +8 | xargs -r rm
echo "✅ Backup process complete!"
