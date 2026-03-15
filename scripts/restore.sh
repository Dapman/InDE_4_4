#!/bin/bash
#
# InDE v3.14 - MongoDB Restore Script
# Restores MongoDB database from a backup archive.
#
# Usage:
#   ./restore.sh                           # List available backups
#   ./restore.sh <backup_file.tar.gz>      # Restore from specified archive
#   ./restore.sh --latest                  # Restore from most recent backup
#
# Environment variables:
#   MONGO_HOST       MongoDB host (default: localhost)
#   MONGO_PORT       MongoDB port (default: 27017)
#   MONGO_DB         Database name (default: inde_db)
#   MONGO_USER       MongoDB username (optional)
#   MONGO_PASSWORD   MongoDB password (optional)
#   BACKUP_DIR       Directory containing backups (default: ./backups)
#

set -e

# Configuration
MONGO_HOST="${MONGO_HOST:-localhost}"
MONGO_PORT="${MONGO_PORT:-27017}"
MONGO_DB="${MONGO_DB:-inde_db}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"

echo "========================================"
echo "InDE v3.14 MongoDB Restore"
echo "========================================"

# Function to list backups
list_backups() {
    echo "Available backups in ${BACKUP_DIR}:"
    echo ""
    if ls "${BACKUP_DIR}"/inde_backup_*.tar.gz 1>/dev/null 2>&1; then
        ls -lh "${BACKUP_DIR}"/inde_backup_*.tar.gz
    else
        echo "No backups found in ${BACKUP_DIR}"
        echo ""
        echo "Create a backup first using: ./backup.sh"
    fi
    echo ""
}

# Function to get latest backup
get_latest_backup() {
    ls -t "${BACKUP_DIR}"/inde_backup_*.tar.gz 2>/dev/null | head -1
}

# No argument - list backups
if [ -z "$1" ]; then
    list_backups
    echo "Usage:"
    echo "  ./restore.sh <backup_file.tar.gz>    Restore from specified archive"
    echo "  ./restore.sh --latest                Restore from most recent backup"
    echo ""
    exit 0
fi

# Handle --latest flag
if [ "$1" = "--latest" ]; then
    BACKUP_FILE=$(get_latest_backup)
    if [ -z "${BACKUP_FILE}" ]; then
        echo "ERROR: No backups found in ${BACKUP_DIR}"
        exit 1
    fi
    echo "Using latest backup: ${BACKUP_FILE}"
else
    BACKUP_FILE="$1"
fi

# Verify backup file exists
if [ ! -f "${BACKUP_FILE}" ]; then
    # Try with backup directory prefix
    if [ -f "${BACKUP_DIR}/${BACKUP_FILE}" ]; then
        BACKUP_FILE="${BACKUP_DIR}/${BACKUP_FILE}"
    else
        echo "ERROR: Backup file not found: ${BACKUP_FILE}"
        echo ""
        list_backups
        exit 1
    fi
fi

echo "Backup file: ${BACKUP_FILE}"
echo "Target database: ${MONGO_DB}"
echo "Host: ${MONGO_HOST}:${MONGO_PORT}"
echo ""

# Confirmation prompt
read -p "WARNING: This will overwrite the current database. Continue? [y/N] " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restore cancelled."
    exit 0
fi

# Create temp directory for extraction
TEMP_DIR=$(mktemp -d)
trap "rm -rf ${TEMP_DIR}" EXIT

echo ""
echo "Extracting backup..."

# Extract the archive
tar -xzf "${BACKUP_FILE}" -C "${TEMP_DIR}"

# Find the extracted directory
RESTORE_DIR=$(find "${TEMP_DIR}" -maxdepth 1 -type d -name "inde_backup_*" | head -1)

if [ -z "${RESTORE_DIR}" ]; then
    echo "ERROR: Invalid backup archive structure"
    exit 1
fi

echo "Restore source: ${RESTORE_DIR}"
echo ""
echo "Starting restore..."

# Build mongorestore command
RESTORE_CMD="mongorestore --host=${MONGO_HOST} --port=${MONGO_PORT} --db=${MONGO_DB} --drop ${RESTORE_DIR}/${MONGO_DB}"

# Add authentication if credentials provided
if [ -n "${MONGO_USER}" ] && [ -n "${MONGO_PASSWORD}" ]; then
    RESTORE_CMD="${RESTORE_CMD} --username=${MONGO_USER} --password=${MONGO_PASSWORD} --authenticationDatabase=admin"
    echo "Using authentication: ${MONGO_USER}"
fi

echo ""

# Run mongorestore
if ${RESTORE_CMD}; then
    echo ""
    echo "========================================"
    echo "Restore completed successfully!"
    echo "========================================"
    echo "Database: ${MONGO_DB}"
    echo "Source: ${BACKUP_FILE}"
    echo ""
    echo "IMPORTANT: Restart the InDE application to ensure"
    echo "           all services pick up the restored data."
    echo ""
else
    echo ""
    echo "ERROR: Restore failed!"
    echo "Please check MongoDB connectivity and permissions."
    exit 1
fi
