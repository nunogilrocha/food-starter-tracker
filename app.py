import json
import os
from flask import Flask, jsonify, request, render_template

app = Flask(__name__)

DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")


def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


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


# --- Food Groups ---

@app.route("/api/food_groups", methods=["GET"])
def get_food_groups():
    data = load_data()
    return jsonify(data["food_groups"])


@app.route("/api/food_groups", methods=["POST"])
def add_food_group():
    data = load_data()
    body = request.json or {}
    if not body.get("name", "").strip():
        return jsonify({"error": "name is required"}), 400
    new_id = max((g["id"] for g in data["food_groups"]), default=0) + 1
    group = {"id": new_id, "name": body["name"].strip(), "color": body.get("color", "#868e96")}
    data["food_groups"].append(group)
    save_data(data)
    return jsonify(group), 201


@app.route("/api/food_groups/<int:group_id>", methods=["PUT"])
def update_food_group(group_id):
    data = load_data()
    for group in data["food_groups"]:
        if group["id"] == group_id:
            body = request.json
            if "name" in body:
                group["name"] = body["name"]
            if "color" in body:
                group["color"] = body["color"]
            save_data(data)
            return jsonify(group)
    return jsonify({"error": "Not found"}), 404


@app.route("/api/food_groups/<int:group_id>", methods=["DELETE"])
def delete_food_group(group_id):
    data = load_data()
    data["food_groups"] = [g for g in data["food_groups"] if g["id"] != group_id]
    # remove entries belonging to this group across all weeks
    for week in data["weeks"]:
        week["entries"] = [e for e in week["entries"] if e["group_id"] != group_id]
    save_data(data)
    return "", 204


# --- Weeks ---

@app.route("/api/weeks", methods=["GET"])
def get_weeks():
    data = load_data()
    return jsonify(data["weeks"])


@app.route("/api/weeks", methods=["POST"])
def add_week():
    data = load_data()
    new_id = max((w["id"] for w in data["weeks"]), default=0) + 1
    body = request.json
    week = {
        "id": new_id,
        "label": body.get("label", f"Week {new_id}"),
        "entries": [],
    }
    data["weeks"].append(week)
    save_data(data)
    return jsonify(week), 201


@app.route("/api/weeks/<int:week_id>", methods=["PUT"])
def update_week(week_id):
    data = load_data()
    for week in data["weeks"]:
        if week["id"] == week_id:
            body = request.json
            if "label" in body:
                week["label"] = body["label"]
            save_data(data)
            return jsonify(week)
    return jsonify({"error": "Not found"}), 404


@app.route("/api/weeks/<int:week_id>", methods=["DELETE"])
def delete_week(week_id):
    data = load_data()
    data["weeks"] = [w for w in data["weeks"] if w["id"] != week_id]
    save_data(data)
    return "", 204


# --- Group Foods ---

@app.route("/api/food_groups/<int:group_id>/foods", methods=["POST"])
def add_group_food(group_id):
    data = load_data()
    body = request.json or {}
    name = body.get("name", "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    for group in data["food_groups"]:
        if group["id"] == group_id:
            if "foods" not in group:
                group["foods"] = []
            food_id = data.get("next_food_id", 1)
            data["next_food_id"] = food_id + 1
            food = {"id": food_id, "name": name}
            group["foods"].append(food)
            save_data(data)
            return jsonify(food), 201
    return jsonify({"error": "Not found"}), 404


@app.route("/api/food_groups/<int:group_id>/foods/<int:food_id>", methods=["DELETE"])
def delete_group_food(group_id, food_id):
    data = load_data()
    for group in data["food_groups"]:
        if group["id"] == group_id:
            group["foods"] = [f for f in group.get("foods", []) if f["id"] != food_id]
            save_data(data)
            return "", 204
    return jsonify({"error": "Not found"}), 404


# --- Entries ---

@app.route("/api/weeks/<int:week_id>/entries", methods=["POST"])
def add_entry(week_id):
    data = load_data()
    body = request.json
    for week in data["weeks"]:
        if week["id"] == week_id:
            entry = {
                "id": data["next_entry_id"],
                "food": body["food"],
                "group_id": body["group_id"],
                "introduced": False,
                "introduced_date": None,
                "notes": body.get("notes", ""),
            }
            data["next_entry_id"] += 1
            week["entries"].append(entry)
            save_data(data)
            return jsonify(entry), 201
    return jsonify({"error": "Week not found"}), 404


@app.route("/api/weeks/<int:week_id>/entries/<int:entry_id>", methods=["PUT"])
def update_entry(week_id, entry_id):
    data = load_data()
    for week in data["weeks"]:
        if week["id"] == week_id:
            for entry in week["entries"]:
                if entry["id"] == entry_id:
                    body = request.json
                    if "food" in body:
                        entry["food"] = body["food"]
                    if "group_id" in body:
                        entry["group_id"] = body["group_id"]
                    if "introduced" in body:
                        entry["introduced"] = body["introduced"]
                    if "introduced_date" in body:
                        entry["introduced_date"] = body["introduced_date"]
                    if "notes" in body:
                        entry["notes"] = body["notes"]
                    save_data(data)
                    return jsonify(entry)
            return jsonify({"error": "Entry not found"}), 404
    return jsonify({"error": "Week not found"}), 404


@app.route("/api/weeks/<int:week_id>/entries/<int:entry_id>", methods=["DELETE"])
def delete_entry(week_id, entry_id):
    data = load_data()
    for week in data["weeks"]:
        if week["id"] == week_id:
            week["entries"] = [e for e in week["entries"] if e["id"] != entry_id]
            save_data(data)
            return "", 204
    return jsonify({"error": "Week not found"}), 404


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
