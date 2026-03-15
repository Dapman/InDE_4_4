#!/bin/bash
#
# InDE v3.14 - MongoDB Backup Script
# Dumps MongoDB database into timestamped archives for self-hosted deployments.
#
# Usage:
#   ./backup.sh                    # Backup to default ./backups directory
#   ./backup.sh /path/to/backups   # Backup to specified directory
#
# Environment variables:
#   MONGO_HOST       MongoDB host (default: localhost)
#   MONGO_PORT       MongoDB port (default: 27017)
#   MONGO_DB         Database name (default: inde_db)
#   MONGO_USER       MongoDB username (optional)
#   MONGO_PASSWORD   MongoDB password (optional)
#   RETENTION_DAYS   Days to keep old backups (default: 30)
#

set -e

# Configuration
MONGO_HOST="${MONGO_HOST:-localhost}"
MONGO_PORT="${MONGO_PORT:-27017}"
MONGO_DB="${MONGO_DB:-inde_db}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

# Backup directory (from argument or default)
BACKUP_DIR="${1:-./backups}"

# Create timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="inde_backup_${TIMESTAMP}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

echo "========================================"
echo "InDE v3.14 MongoDB Backup"
echo "========================================"
echo "Timestamp: ${TIMESTAMP}"
echo "Database: ${MONGO_DB}"
echo "Host: ${MONGO_HOST}:${MONGO_PORT}"
echo "Backup path: ${BACKUP_PATH}"
echo ""

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Build mongodump command
DUMP_CMD="mongodump --host=${MONGO_HOST} --port=${MONGO_PORT} --db=${MONGO_DB} --out=${BACKUP_PATH}"

# Add authentication if credentials provided
if [ -n "${MONGO_USER}" ] && [ -n "${MONGO_PASSWORD}" ]; then
    DUMP_CMD="${DUMP_CMD} --username=${MONGO_USER} --password=${MONGO_PASSWORD} --authenticationDatabase=admin"
    echo "Using authentication: ${MONGO_USER}"
fi

echo ""
echo "Starting backup..."

# Run mongodump
if ${DUMP_CMD}; then
    echo ""
    echo "Dump completed. Compressing..."

    # Compress the backup
    cd "${BACKUP_DIR}"
    tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}"
    rm -rf "${BACKUP_NAME}"

    FINAL_PATH="${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
    BACKUP_SIZE=$(du -h "${FINAL_PATH}" | cut -f1)

    echo ""
    echo "========================================"
    echo "Backup completed successfully!"
    echo "========================================"
    echo "Archive: ${FINAL_PATH}"
    echo "Size: ${BACKUP_SIZE}"
    echo ""

    # Cleanup old backups
    if [ "${RETENTION_DAYS}" -gt 0 ]; then
        echo "Cleaning up backups older than ${RETENTION_DAYS} days..."
        find "${BACKUP_DIR}" -name "inde_backup_*.tar.gz" -type f -mtime +${RETENTION_DAYS} -delete
        echo "Cleanup complete."
    fi

    # List recent backups
    echo ""
    echo "Recent backups:"
    ls -lh "${BACKUP_DIR}"/inde_backup_*.tar.gz 2>/dev/null | tail -5 || echo "No backups found"
    echo ""

else
    echo ""
    echo "ERROR: Backup failed!"
    echo "Please check MongoDB connectivity and permissions."
    exit 1
fi
