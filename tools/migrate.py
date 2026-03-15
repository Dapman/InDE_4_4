#!/usr/bin/env python3
"""
InDE Build Harness - Database Migration Tool

Manages schema migrations for InDE MongoDB collections.
Tracks applied migrations in a '_migrations' collection.

Usage:
    python tools/migrate.py status          # Show migration status
    python tools/migrate.py up              # Apply all pending migrations
    python tools/migrate.py up --to 002     # Apply up to specific migration
    python tools/migrate.py down            # Rollback last migration
    python tools/migrate.py down --to 001   # Rollback to specific migration
"""

import argparse
import importlib.util
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

try:
    from pymongo import MongoClient
except ImportError:
    print("Error: pymongo not installed. Run: pip install pymongo")
    sys.exit(1)


class Migration:
    """Base class for migrations."""

    version: str = "000"
    name: str = "base"
    description: str = ""

    def up(self, db) -> bool:
        """Apply migration. Return True if successful."""
        raise NotImplementedError

    def down(self, db) -> bool:
        """Rollback migration. Return True if successful."""
        raise NotImplementedError


class MigrationRunner:
    """Runs migrations against MongoDB."""

    MIGRATIONS_COLLECTION = "_migrations"

    def __init__(self, mongo_uri: str = None):
        self.mongo_uri = mongo_uri or os.environ.get(
            "MONGO_URI", "mongodb://localhost:27017/inde"
        )
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client.get_database()
        self.migrations_dir = Path(__file__).parent / "migrations"

    def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration versions."""
        migrations = self.db[self.MIGRATIONS_COLLECTION].find(
            {"status": "applied"},
            {"version": 1}
        ).sort("version", 1)
        return [m["version"] for m in migrations]

    def get_available_migrations(self) -> List[Dict]:
        """Discover available migration files."""
        migrations = []

        if not self.migrations_dir.exists():
            return migrations

        for file in sorted(self.migrations_dir.glob("*.py")):
            if file.name.startswith("_"):
                continue

            # Extract version from filename (e.g., "001_v3_5_0_initial.py")
            parts = file.stem.split("_", 1)
            if len(parts) < 2 or not parts[0].isdigit():
                continue

            version = parts[0]

            # Load the migration module
            spec = importlib.util.spec_from_file_location(
                f"migration_{version}", file
            )
            module = importlib.util.module_from_spec(spec)

            try:
                spec.loader.exec_module(module)
            except Exception as e:
                print(f"Warning: Failed to load migration {file.name}: {e}")
                continue

            # Find Migration class
            migration_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                    issubclass(attr, Migration) and
                    attr is not Migration):
                    migration_class = attr
                    break

            if migration_class:
                migrations.append({
                    "version": version,
                    "file": file.name,
                    "class": migration_class,
                    "description": getattr(migration_class, "description", "")
                })

        return migrations

    def status(self) -> None:
        """Print migration status."""
        applied = set(self.get_applied_migrations())
        available = self.get_available_migrations()

        print("=" * 60)
        print("InDE Database Migration Status")
        print("=" * 60)
        print(f"Database: {self.mongo_uri}")
        print()

        if not available:
            print("No migrations found.")
            return

        print(f"{'Version':<10} {'Status':<12} {'Description'}")
        print("-" * 60)

        for mig in available:
            status = "applied" if mig["version"] in applied else "pending"
            status_marker = "[OK]" if status == "applied" else "[--]"
            print(f"{mig['version']:<10} {status_marker:<12} {mig['description'][:40]}")

        pending_count = len([m for m in available if m["version"] not in applied])
        print()
        print(f"Applied: {len(applied)}, Pending: {pending_count}")

    def up(self, target: Optional[str] = None) -> int:
        """Apply pending migrations up to target (or all)."""
        applied = set(self.get_applied_migrations())
        available = self.get_available_migrations()

        pending = [m for m in available if m["version"] not in applied]

        if target:
            pending = [m for m in pending if m["version"] <= target]

        if not pending:
            print("No pending migrations.")
            return 0

        print(f"Applying {len(pending)} migration(s)...")
        print()

        applied_count = 0
        for mig in pending:
            print(f"[{mig['version']}] {mig['description']}...", end=" ")

            try:
                instance = mig["class"]()
                result = instance.up(self.db)

                if result:
                    # Record successful migration
                    self.db[self.MIGRATIONS_COLLECTION].insert_one({
                        "version": mig["version"],
                        "file": mig["file"],
                        "description": mig["description"],
                        "status": "applied",
                        "applied_at": datetime.now(timezone.utc)
                    })
                    print("OK")
                    applied_count += 1
                else:
                    print("FAILED (returned False)")
                    break

            except Exception as e:
                print(f"FAILED: {e}")
                break

        print()
        print(f"Applied {applied_count} migration(s).")
        return applied_count

    def down(self, target: Optional[str] = None) -> int:
        """Rollback migrations down to target (or last one)."""
        applied = self.get_applied_migrations()
        available = {m["version"]: m for m in self.get_available_migrations()}

        if not applied:
            print("No migrations to rollback.")
            return 0

        # Determine which to rollback
        if target:
            to_rollback = [v for v in reversed(applied) if v > target]
        else:
            to_rollback = [applied[-1]]  # Just the last one

        if not to_rollback:
            print("No migrations to rollback.")
            return 0

        print(f"Rolling back {len(to_rollback)} migration(s)...")
        print()

        rolled_back = 0
        for version in to_rollback:
            mig = available.get(version)
            if not mig:
                print(f"[{version}] Migration file not found, skipping...")
                continue

            print(f"[{version}] Rolling back {mig['description']}...", end=" ")

            try:
                instance = mig["class"]()
                result = instance.down(self.db)

                if result:
                    # Remove from applied
                    self.db[self.MIGRATIONS_COLLECTION].update_one(
                        {"version": version},
                        {"$set": {
                            "status": "rolled_back",
                            "rolled_back_at": datetime.now(timezone.utc)
                        }}
                    )
                    print("OK")
                    rolled_back += 1
                else:
                    print("FAILED (returned False)")
                    break

            except Exception as e:
                print(f"FAILED: {e}")
                break

        print()
        print(f"Rolled back {rolled_back} migration(s).")
        return rolled_back


def main():
    parser = argparse.ArgumentParser(description="InDE Database Migration Tool")
    parser.add_argument("command", choices=["status", "up", "down"],
                        help="Migration command")
    parser.add_argument("--to", dest="target",
                        help="Target version (for up/down)")
    parser.add_argument("--mongo-uri",
                        help="MongoDB URI (default: from MONGO_URI env)")

    args = parser.parse_args()

    runner = MigrationRunner(args.mongo_uri)

    if args.command == "status":
        runner.status()
    elif args.command == "up":
        runner.up(args.target)
    elif args.command == "down":
        runner.down(args.target)


if __name__ == "__main__":
    main()
