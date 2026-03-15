#!/bin/bash
# migrate_v315_data.sh - Import v3.15 user data into v3.16
# Run this AFTER v3.16 containers are up and running

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ARCHIVE_FILE="$PROJECT_DIR/data_migration_v315.archive"
MONGO_CONTAINER="inde-db"

echo "=== InDE v3.15 -> v3.16 Data Migration ==="

# Check if archive exists
if [ ! -f "$ARCHIVE_FILE" ]; then
    echo "ERROR: Migration archive not found at $ARCHIVE_FILE"
    exit 1
fi

# Check if MongoDB container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${MONGO_CONTAINER}$"; then
    echo "ERROR: MongoDB container '$MONGO_CONTAINER' is not running"
    echo "Start v3.16 containers first: docker compose up -d"
    exit 1
fi

# Copy archive to container
echo "Copying archive to MongoDB container..."
docker cp "$ARCHIVE_FILE" "$MONGO_CONTAINER:/tmp/data_migration_v315.archive"

# Restore data
echo "Restoring data from v3.15..."
docker exec "$MONGO_CONTAINER" mongorestore \
    --archive=/tmp/data_migration_v315.archive \
    --drop \
    --db inde

# Verify restoration
echo ""
echo "=== Migration Complete ==="
echo "Verifying data:"
docker exec "$MONGO_CONTAINER" mongosh inde --quiet --eval '
print("Users:", db.users.countDocuments({}));
print("Pursuits:", db.pursuits.countDocuments({}));
print("Conversations:", db.conversation_history.countDocuments({}));
print("Artifacts:", db.artifacts.countDocuments({}));
'

# Cleanup
docker exec "$MONGO_CONTAINER" rm -f /tmp/data_migration_v315.archive

echo ""
echo "Data migration from v3.15 complete!"
