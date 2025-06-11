import os
import sys
import logging
from pathlib import Path
from neo4j import GraphDatabase
from typing import List, Dict, Any

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Neo4jMigrationRunner:
    """Neo4j migration runner similar to Alembic for SQL databases."""
    
    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "password")),
        )
        self.migrations_dir = Path(__file__).parent / "versions"
        self.migrations_dir.mkdir(exist_ok=True)
        
    def _ensure_migration_table(self):
        """Create migration tracking node if it doesn't exist."""
        with self.driver.session() as session:
            session.run("""
                MERGE (m:MigrationHistory {id: 'neo4j_migrations'})
                ON CREATE SET m.applied_migrations = [], m.created_at = datetime()
                RETURN m
            """)
    
    def _get_applied_migrations(self) -> List[str]:
        """Get list of applied migration IDs."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (m:MigrationHistory {id: 'neo4j_migrations'})
                RETURN m.applied_migrations as migrations
            """)
            record = result.single()
            return record["migrations"] if record else []
    
    def _mark_migration_applied(self, migration_id: str):
        """Mark a migration as applied."""
        with self.driver.session() as session:
            session.run("""
                MATCH (m:MigrationHistory {id: 'neo4j_migrations'})
                SET m.applied_migrations = m.applied_migrations + $migration_id,
                    m.last_updated = datetime()
            """, migration_id=migration_id)
    
    def _mark_migration_reverted(self, migration_id: str):
        """Mark a migration as reverted."""
        with self.driver.session() as session:
            session.run("""
                MATCH (m:MigrationHistory {id: 'neo4j_migrations'})
                SET m.applied_migrations = [x IN m.applied_migrations WHERE x <> $migration_id],
                    m.last_updated = datetime()
            """, migration_id=migration_id)
    
    def get_pending_migrations(self) -> List[Dict[str, Any]]:
        """Get list of pending migrations."""
        applied = set(self._get_applied_migrations())
        pending = []
        
        for migration_file in sorted(self.migrations_dir.glob("*.py")):
            if migration_file.name.startswith("__"):
                continue
                
            migration_id = migration_file.stem
            if migration_id not in applied:
                pending.append({
                    "id": migration_id,
                    "file": migration_file,
                    "name": migration_id.split("_", 1)[1] if "_" in migration_id else migration_id
                })
        
        return pending
    
    def run_migration(self, migration_file: Path, direction: str = "upgrade"):
        """Run a single migration file."""
        logger.info(f"Running {direction} for migration: {migration_file.name}")
        
        # Import the migration module
        spec = __import__(f"versions.{migration_file.stem}", fromlist=["upgrade", "downgrade"])
        
        with self.driver.session() as session:
            if direction == "upgrade":
                if hasattr(spec, 'upgrade'):
                    spec.upgrade(session)
                    self._mark_migration_applied(migration_file.stem)
                    logger.info(f"Applied migration: {migration_file.stem}")
                else:
                    logger.warning(f"No upgrade function found in {migration_file.name}")
            elif direction == "downgrade":
                if hasattr(spec, 'downgrade'):
                    spec.downgrade(session)
                    self._mark_migration_reverted(migration_file.stem)
                    logger.info(f"Reverted migration: {migration_file.stem}")
                else:
                    logger.warning(f"No downgrade function found in {migration_file.name}")
    
    def upgrade(self, target: str = "head"):
        """Run all pending migrations."""
        self._ensure_migration_table()
        pending = self.get_pending_migrations()
        
        if not pending:
            logger.info("No pending migrations to apply")
            return
        
        logger.info(f"Applying {len(pending)} pending migrations...")
        for migration in pending:
            self.run_migration(migration["file"], "upgrade")
    
    def downgrade(self, target: str = None):
        """Revert migrations."""
        self._ensure_migration_table()
        applied = self._get_applied_migrations()
        
        if not applied:
            logger.info("No migrations to revert")
            return
        
        # For simplicity, revert the last migration
        # In a full implementation, you'd handle target specification
        last_migration = applied[-1]
        migration_file = self.migrations_dir / f"{last_migration}.py"
        
        if migration_file.exists():
            self.run_migration(migration_file, "downgrade")
        else:
            logger.error(f"Migration file not found: {migration_file}")
    
    def current(self):
        """Show current migration state."""
        self._ensure_migration_table()
        applied = self._get_applied_migrations()
        
        if applied:
            logger.info(f"Current migration: {applied[-1]}")
            logger.info(f"Total applied migrations: {len(applied)}")
        else:
            logger.info("No migrations applied")
        
        return applied
    
    def history(self):
        """Show migration history."""
        self._ensure_migration_table()
        applied = self._get_applied_migrations()
        
        logger.info("Migration History:")
        for i, migration_id in enumerate(applied, 1):
            logger.info(f"  {i}. {migration_id}")
        
        return applied
    
    def close(self):
        """Close the Neo4j driver."""
        self.driver.close()

def run_migrations_upgrade():
    """Run upgrade migrations."""
    runner = Neo4jMigrationRunner()
    try:
        runner.upgrade()
    finally:
        runner.close()

def run_migrations_downgrade():
    """Run downgrade migrations."""
    runner = Neo4jMigrationRunner()
    try:
        runner.downgrade()
    finally:
        runner.close()

def show_current():
    """Show current migration state."""
    runner = Neo4jMigrationRunner()
    try:
        return runner.current()
    finally:
        runner.close()

def show_history():
    """Show migration history."""
    runner = Neo4jMigrationRunner()
    try:
        return runner.history()
    finally:
        runner.close() 