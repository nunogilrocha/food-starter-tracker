from sqlite_migrate import Migrations

migration = Migrations("food_tracker")


@migration()
def create_initial_schema(db):
    """Create all tables for the initial schema."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS food_groups (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name  TEXT    NOT NULL,
            color TEXT    NOT NULL DEFAULT '#868e96'
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS group_foods (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL REFERENCES food_groups(id) ON DELETE CASCADE,
            name     TEXT    NOT NULL
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS weeks (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT    NOT NULL
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            week_id         INTEGER NOT NULL REFERENCES weeks(id)       ON DELETE CASCADE,
            food            TEXT    NOT NULL,
            group_id        INTEGER NOT NULL REFERENCES food_groups(id) ON DELETE CASCADE,
            introduced      INTEGER NOT NULL DEFAULT 0,
            introduced_date TEXT,
            notes           TEXT    NOT NULL DEFAULT ''
        )
    """)
