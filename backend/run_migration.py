"""
Run Database Migration
Applies schema changes to extend QueryHistory table and create experiment schema
"""
import sys
from pathlib import Path

# Add backend to Python path
backend_dir = Path(__file__).parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from utils.database import db
from utils.logger import logger


def run_migration(migration_file: Path, description: str):
    """Run a single database migration"""
    if not migration_file.exists():
        logger.error(f"Migration file not found: {migration_file}")
        return False

    try:
        logger.info(f"Reading migration file: {migration_file.name}...")
        with open(migration_file, 'r') as f:
            migration_sql = f.read()

        logger.info(f"Executing migration: {description}...")
        db.execute_raw(migration_sql)

        logger.info(f"✅ Migration completed: {description}")
        return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False


def run_all_migrations():
    """Run all database migrations in order"""
    migrations = [
        {
            "file": backend_dir / "database" / "migrations" / "001_extend_query_history.sql",
            "description": "Extend QueryHistory table",
        },
        {
            "file": backend_dir / "database" / "migrations" / "002_create_experiment_schema.sql",
            "description": "Create Experiment schema for user study",
        },
        {
            "file": backend_dir / "database" / "migrations" / "003_add_participant_onboarding_fields.sql",
            "description": "Add participant onboarding fields",
        },
        {
            "file": backend_dir / "database" / "migrations" / "004_add_participant_id_to_query_history.sql",
            "description": "Add participant_id to query_history",
        },
        {
            "file": backend_dir / "database" / "migrations" / "005_add_presurvey_fields.sql",
            "description": "Add pre-survey fields (replace PII with anonymous data)",
        },
    ]

    results = []
    for migration in migrations:
        success = run_migration(migration["file"], migration["description"])
        results.append({"name": migration["file"].name, "success": success, "description": migration["description"]})

    return results


if __name__ == "__main__":
    print("=" * 80)
    print("Database Migration Runner")
    print("=" * 80)
    print()

    results = run_all_migrations()

    print()
    print("=" * 80)
    print("Migration Results")
    print("=" * 80)

    all_success = True
    for result in results:
        status = "✅" if result["success"] else "❌"
        print(f"  {status} {result['name']}: {result['description']}")
        if not result["success"]:
            all_success = False

    print()
    if all_success:
        print("✅ All migrations completed successfully!")
        print()
        print("Changes applied:")
        print("  - Extended QueryHistory table with thesis analysis fields")
        print("  - Added role column to users table")
        print("  - Created experiments table")
        print("  - Created experiment_participants table")
        print("  - Created experiment_tasks table")
        print("  - Created experiment_interactions table")
        print("  - Linked query_history to experiment_tasks")
        print("  - Added participant onboarding fields (legacy)")
        print("  - Added participant_id to query_history")
        print("  - Added pre-survey fields (age_range, occupation_status, etc.)")
        sys.exit(0)
    else:
        print("❌ Some migrations failed. Check logs for details.")
        sys.exit(1)
