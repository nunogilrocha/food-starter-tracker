"""
One-time migration: data.json → data.db

Run once:  python3 migrate.py
"""
import json
import os
import sqlite3

BASE = os.path.dirname(__file__)
JSON_FILE = os.path.join(BASE, "data.json")
DB_FILE   = os.path.join(BASE, "data.db")

if not os.path.exists(JSON_FILE):
    print("data.json not found — nothing to migrate.")
    raise SystemExit(0)

if os.path.exists(DB_FILE):
    answer = input("data.db already exists. Overwrite? [y/N] ").strip().lower()
    if answer != "y":
        print("Aborted.")
        raise SystemExit(0)
    os.remove(DB_FILE)

with open(JSON_FILE) as f:
    data = json.load(f)

db = sqlite3.connect(DB_FILE)
db.execute("PRAGMA foreign_keys = ON")
db.executescript("""
    CREATE TABLE food_groups (
        id    INTEGER PRIMARY KEY AUTOINCREMENT,
        name  TEXT    NOT NULL,
        color TEXT    NOT NULL DEFAULT '#868e96'
    );
    CREATE TABLE group_foods (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER NOT NULL REFERENCES food_groups(id) ON DELETE CASCADE,
        name     TEXT    NOT NULL
    );
    CREATE TABLE weeks (
        id    INTEGER PRIMARY KEY AUTOINCREMENT,
        label TEXT    NOT NULL
    );
    CREATE TABLE entries (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        week_id         INTEGER NOT NULL REFERENCES weeks(id)       ON DELETE CASCADE,
        food            TEXT    NOT NULL,
        group_id        INTEGER NOT NULL REFERENCES food_groups(id) ON DELETE CASCADE,
        introduced      INTEGER NOT NULL DEFAULT 0,
        introduced_date TEXT,
        notes           TEXT    NOT NULL DEFAULT ''
    );
""")

for g in data.get("food_groups", []):
    db.execute(
        "INSERT INTO food_groups (id, name, color) VALUES (?, ?, ?)",
        (g["id"], g["name"], g.get("color", "#868e96"))
    )
    for f in g.get("foods", []):
        db.execute(
            "INSERT INTO group_foods (id, group_id, name) VALUES (?, ?, ?)",
            (f["id"], g["id"], f["name"])
        )

for w in data.get("weeks", []):
    db.execute("INSERT INTO weeks (id, label) VALUES (?, ?)", (w["id"], w["label"]))
    for e in w.get("entries", []):
        db.execute(
            "INSERT INTO entries (id, week_id, food, group_id, introduced, introduced_date, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (e["id"], w["id"], e["food"], e["group_id"],
             int(e.get("introduced", False)), e.get("introduced_date"), e.get("notes", ""))
        )

db.commit()
db.close()

groups  = len(data.get("food_groups", []))
weeks   = len(data.get("weeks", []))
entries = sum(len(w.get("entries", [])) for w in data.get("weeks", []))
print(f"Migrated: {groups} groups, {weeks} weeks, {entries} entries → data.db")
