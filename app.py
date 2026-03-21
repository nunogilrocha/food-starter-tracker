import sqlite3
import os
import sqlite_utils
from flask import Flask, jsonify, request, render_template
from migrations import migration

app = Flask(__name__)

DB_FILE = os.path.join(os.path.dirname(__file__), "data.db")


def get_db():
    db = sqlite3.connect(DB_FILE)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def init_db():
    migration.apply(sqlite_utils.Database(DB_FILE))


init_db()


# ── Helpers ────────────────────────────────────────────────────────────────

def _group_to_dict(row, db):
    g = dict(row)
    foods = db.execute(
        "SELECT id, name FROM group_foods WHERE group_id = ? ORDER BY id",
        (g["id"],)
    ).fetchall()
    g["foods"] = [dict(f) for f in foods]
    return g


def _week_to_dict(row, db):
    w = dict(row)
    rows = db.execute(
        "SELECT id, food, group_id, introduced, introduced_date, notes "
        "FROM entries WHERE week_id = ? ORDER BY id",
        (w["id"],)
    ).fetchall()
    w["entries"] = [
        {**dict(e), "introduced": bool(e["introduced"])}
        for e in rows
    ]
    return w


# ── Routes ─────────────────────────────────────────────────────────────────

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/calendar")
def view_calendar():
    return render_template("index.html", initial_tab="calendar")


@app.route("/groups")
def view_groups():
    return render_template("index.html", initial_tab="groups")


@app.route("/list")
def view_list():
    return render_template("index.html", initial_tab="foodlist")


# ── Food Groups ────────────────────────────────────────────────────────────

@app.route("/api/food_groups", methods=["GET"])
def get_food_groups():
    db = get_db()
    rows = db.execute("SELECT id, name, color FROM food_groups ORDER BY id").fetchall()
    result = [_group_to_dict(r, db) for r in rows]
    db.close()
    return jsonify(result)


@app.route("/api/food_groups", methods=["POST"])
def add_food_group():
    body = request.json or {}
    name = body.get("name", "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    color = body.get("color", "#868e96")
    db = get_db()
    cur = db.execute("INSERT INTO food_groups (name, color) VALUES (?, ?)", (name, color))
    db.commit()
    group = {"id": cur.lastrowid, "name": name, "color": color, "foods": []}
    db.close()
    return jsonify(group), 201


@app.route("/api/food_groups/<int:group_id>", methods=["PUT"])
def update_food_group(group_id):
    body = request.json or {}
    db = get_db()
    row = db.execute("SELECT id, name, color FROM food_groups WHERE id = ?", (group_id,)).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "Not found"}), 404
    name  = body.get("name",  row["name"])
    color = body.get("color", row["color"])
    db.execute("UPDATE food_groups SET name = ?, color = ? WHERE id = ?", (name, color, group_id))
    db.commit()
    result = _group_to_dict(
        db.execute("SELECT id, name, color FROM food_groups WHERE id = ?", (group_id,)).fetchone(), db
    )
    db.close()
    return jsonify(result)


@app.route("/api/food_groups/<int:group_id>", methods=["DELETE"])
def delete_food_group(group_id):
    # CASCADE deletes group_foods and entries automatically
    db = get_db()
    db.execute("DELETE FROM food_groups WHERE id = ?", (group_id,))
    db.commit()
    db.close()
    return "", 204


# ── Group Foods ────────────────────────────────────────────────────────────

@app.route("/api/food_groups/<int:group_id>/foods", methods=["POST"])
def add_group_food(group_id):
    body = request.json or {}
    name = body.get("name", "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    db = get_db()
    if not db.execute("SELECT 1 FROM food_groups WHERE id = ?", (group_id,)).fetchone():
        db.close()
        return jsonify({"error": "Not found"}), 404
    cur = db.execute("INSERT INTO group_foods (group_id, name) VALUES (?, ?)", (group_id, name))
    db.commit()
    food = {"id": cur.lastrowid, "name": name}
    db.close()
    return jsonify(food), 201


@app.route("/api/food_groups/<int:group_id>/foods/<int:food_id>", methods=["DELETE"])
def delete_group_food(group_id, food_id):
    db = get_db()
    db.execute("DELETE FROM group_foods WHERE id = ? AND group_id = ?", (food_id, group_id))
    db.commit()
    db.close()
    return "", 204


# ── Weeks ──────────────────────────────────────────────────────────────────

@app.route("/api/weeks", methods=["GET"])
def get_weeks():
    db = get_db()
    rows = db.execute("SELECT id, label FROM weeks ORDER BY id").fetchall()
    result = [_week_to_dict(r, db) for r in rows]
    db.close()
    return jsonify(result)


@app.route("/api/weeks", methods=["POST"])
def add_week():
    body = request.json or {}
    db = get_db()
    count = db.execute("SELECT COUNT(*) FROM weeks").fetchone()[0]
    label = body.get("label", f"Week {count + 1}")
    cur = db.execute("INSERT INTO weeks (label) VALUES (?)", (label,))
    db.commit()
    week = {"id": cur.lastrowid, "label": label, "entries": []}
    db.close()
    return jsonify(week), 201


@app.route("/api/weeks/<int:week_id>", methods=["PUT"])
def update_week(week_id):
    body = request.json or {}
    db = get_db()
    row = db.execute("SELECT id, label FROM weeks WHERE id = ?", (week_id,)).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "Not found"}), 404
    label = body.get("label", row["label"])
    db.execute("UPDATE weeks SET label = ? WHERE id = ?", (label, week_id))
    db.commit()
    result = _week_to_dict(
        db.execute("SELECT id, label FROM weeks WHERE id = ?", (week_id,)).fetchone(), db
    )
    db.close()
    return jsonify(result)


@app.route("/api/weeks/<int:week_id>", methods=["DELETE"])
def delete_week(week_id):
    # CASCADE deletes entries automatically
    db = get_db()
    db.execute("DELETE FROM weeks WHERE id = ?", (week_id,))
    db.commit()
    db.close()
    return "", 204


# ── Entries ────────────────────────────────────────────────────────────────

@app.route("/api/weeks/<int:week_id>/entries", methods=["POST"])
def add_entry(week_id):
    body = request.json or {}
    db = get_db()
    if not db.execute("SELECT 1 FROM weeks WHERE id = ?", (week_id,)).fetchone():
        db.close()
        return jsonify({"error": "Week not found"}), 404
    cur = db.execute(
        "INSERT INTO entries (week_id, food, group_id, introduced, introduced_date, notes) "
        "VALUES (?, ?, ?, 0, NULL, ?)",
        (week_id, body["food"], body["group_id"], body.get("notes", ""))
    )
    db.commit()
    entry = {
        "id": cur.lastrowid,
        "food": body["food"],
        "group_id": body["group_id"],
        "introduced": False,
        "introduced_date": None,
        "notes": body.get("notes", ""),
    }
    db.close()
    return jsonify(entry), 201


@app.route("/api/weeks/<int:week_id>/entries/<int:entry_id>", methods=["PUT"])
def update_entry(week_id, entry_id):
    body = request.json or {}
    db = get_db()
    if not db.execute("SELECT 1 FROM weeks WHERE id = ?", (week_id,)).fetchone():
        db.close()
        return jsonify({"error": "Week not found"}), 404
    row = db.execute(
        "SELECT id, food, group_id, introduced, introduced_date, notes "
        "FROM entries WHERE id = ? AND week_id = ?",
        (entry_id, week_id)
    ).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "Entry not found"}), 404
    food     = body.get("food",            row["food"])
    group_id = body.get("group_id",        row["group_id"])
    intro    = body.get("introduced",      bool(row["introduced"]))
    date     = body.get("introduced_date", row["introduced_date"])
    notes    = body.get("notes",           row["notes"])
    db.execute(
        "UPDATE entries SET food=?, group_id=?, introduced=?, introduced_date=?, notes=? WHERE id=?",
        (food, group_id, int(intro), date, notes, entry_id)
    )
    db.commit()
    db.close()
    return jsonify({
        "id": entry_id, "food": food, "group_id": group_id,
        "introduced": intro, "introduced_date": date, "notes": notes,
    })


@app.route("/api/weeks/<int:week_id>/entries/<int:entry_id>", methods=["DELETE"])
def delete_entry(week_id, entry_id):
    db = get_db()
    if not db.execute("SELECT 1 FROM weeks WHERE id = ?", (week_id,)).fetchone():
        db.close()
        return jsonify({"error": "Week not found"}), 404
    db.execute("DELETE FROM entries WHERE id = ? AND week_id = ?", (entry_id, week_id))
    db.commit()
    db.close()
    return "", 204


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
