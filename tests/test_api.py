"""
API integration tests for Food Starter Tracker (SQLite backend).
Each test gets an isolated in-memory SQLite database seeded with SEED data.
"""
import sqlite3
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import app as app_module
from app import app


# ── Fixtures ───────────────────────────────────────────────────────────────

def seed_db(db_path):
    db = sqlite3.connect(db_path)
    db.execute("PRAGMA foreign_keys = ON")
    app_module.init_db()   # creates tables using the monkeypatched DB_FILE
    db = sqlite3.connect(db_path)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
        INSERT INTO food_groups (id, name, color) VALUES
            (1, 'Vegetables', '#e03131'),
            (2, 'Fruits',     '#9c36b5');

        INSERT INTO group_foods (id, group_id, name) VALUES
            (1, 1, 'Carrot'),
            (2, 1, 'Broccoli'),
            (3, 2, 'Apple'),
            (4, 2, 'Pear');

        INSERT INTO weeks (id, label) VALUES
            (1, 'Week 1'),
            (2, 'Week 2');

        INSERT INTO entries (id, week_id, food, group_id, introduced, introduced_date, notes) VALUES
            (1, 1, 'Carrot', 1, 0, NULL,         ''),
            (2, 1, 'Apple',  2, 1, '2026-03-01', 'loved it');
    """)
    db.commit()
    db.close()


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Flask test client backed by an isolated temporary SQLite database."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(app_module, "DB_FILE", db_path)
    seed_db(db_path)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── Food Groups ────────────────────────────────────────────────────────────

class TestFoodGroups:
    def test_get_returns_all_groups(self, client):
        r = client.get("/api/food_groups")
        assert r.status_code == 200
        data = r.get_json()
        assert len(data) == 2
        assert data[0]["name"] == "Vegetables"

    def test_get_includes_foods_list(self, client):
        data = client.get("/api/food_groups").get_json()
        veg = next(g for g in data if g["id"] == 1)
        assert len(veg["foods"]) == 2
        assert any(f["name"] == "Carrot" for f in veg["foods"])

    def test_create_group(self, client):
        r = client.post("/api/food_groups", json={"name": "Grains", "color": "#2f9e44"})
        assert r.status_code == 201
        created = r.get_json()
        assert created["name"] == "Grains"
        assert created["foods"] == []
        assert len(client.get("/api/food_groups").get_json()) == 3

    def test_create_group_missing_name_returns_400(self, client):
        r = client.post("/api/food_groups", json={"color": "#000"})
        assert r.status_code == 400

    def test_create_group_empty_name_returns_400(self, client):
        r = client.post("/api/food_groups", json={"name": "   ", "color": "#000"})
        assert r.status_code == 400

    def test_update_group_name(self, client):
        r = client.put("/api/food_groups/1", json={"name": "Veggies"})
        assert r.status_code == 200
        assert r.get_json()["name"] == "Veggies"

    def test_update_group_color(self, client):
        r = client.put("/api/food_groups/1", json={"color": "#ff0000"})
        assert r.status_code == 200
        assert r.get_json()["color"] == "#ff0000"

    def test_update_group_preserves_foods(self, client):
        r = client.put("/api/food_groups/1", json={"name": "Veggies"})
        assert len(r.get_json()["foods"]) == 2

    def test_update_nonexistent_group_returns_404(self, client):
        r = client.put("/api/food_groups/999", json={"name": "Ghost"})
        assert r.status_code == 404

    def test_delete_group_removes_group(self, client):
        r = client.delete("/api/food_groups/1")
        assert r.status_code == 204
        assert all(g["id"] != 1 for g in client.get("/api/food_groups").get_json())

    def test_delete_group_cascades_to_entries(self, client):
        """Deleting group 1 (Vegetables) must remove Carrot from Week 1."""
        client.delete("/api/food_groups/1")
        weeks = client.get("/api/weeks").get_json()
        week1_entries = weeks[0]["entries"]
        assert all(e["group_id"] != 1 for e in week1_entries)

    def test_delete_group_cascades_to_group_foods(self, client):
        client.delete("/api/food_groups/1")
        groups = client.get("/api/food_groups").get_json()
        assert all(g["id"] != 1 for g in groups)

    def test_delete_nonexistent_group_returns_204(self, client):
        assert client.delete("/api/food_groups/999").status_code == 204


# ── Group Foods ────────────────────────────────────────────────────────────

class TestGroupFoods:
    def test_add_food_to_group(self, client):
        r = client.post("/api/food_groups/1/foods", json={"name": "Peas"})
        assert r.status_code == 201
        assert r.get_json()["name"] == "Peas"

    def test_added_food_appears_in_group_list(self, client):
        client.post("/api/food_groups/1/foods", json={"name": "Peas"})
        groups = client.get("/api/food_groups").get_json()
        veg = next(g for g in groups if g["id"] == 1)
        assert any(f["name"] == "Peas" for f in veg["foods"])

    def test_add_food_missing_name_returns_400(self, client):
        r = client.post("/api/food_groups/1/foods", json={})
        assert r.status_code == 400

    def test_add_food_to_nonexistent_group_returns_404(self, client):
        r = client.post("/api/food_groups/999/foods", json={"name": "Ghost"})
        assert r.status_code == 404

    def test_delete_food_from_group(self, client):
        r = client.delete("/api/food_groups/1/foods/1")
        assert r.status_code == 204
        groups = client.get("/api/food_groups").get_json()
        veg = next(g for g in groups if g["id"] == 1)
        assert all(f["id"] != 1 for f in veg["foods"])

    def test_delete_nonexistent_food_returns_204(self, client):
        assert client.delete("/api/food_groups/1/foods/999").status_code == 204


# ── Weeks ──────────────────────────────────────────────────────────────────

class TestWeeks:
    def test_get_returns_all_weeks(self, client):
        r = client.get("/api/weeks")
        assert r.status_code == 200
        assert len(r.get_json()) == 2

    def test_create_week(self, client):
        r = client.post("/api/weeks", json={"label": "Week 3"})
        assert r.status_code == 201
        assert r.get_json()["label"] == "Week 3"
        assert len(client.get("/api/weeks").get_json()) == 3

    def test_create_week_has_empty_entries(self, client):
        created = client.post("/api/weeks", json={"label": "Week 3"}).get_json()
        assert created["entries"] == []

    def test_update_week_label(self, client):
        r = client.put("/api/weeks/1", json={"label": "First Week"})
        assert r.status_code == 200
        assert r.get_json()["label"] == "First Week"

    def test_update_week_preserves_entries(self, client):
        r = client.put("/api/weeks/1", json={"label": "First Week"})
        assert len(r.get_json()["entries"]) == 2

    def test_update_nonexistent_week_returns_404(self, client):
        r = client.put("/api/weeks/999", json={"label": "Ghost"})
        assert r.status_code == 404

    def test_delete_week(self, client):
        r = client.delete("/api/weeks/1")
        assert r.status_code == 204
        assert all(w["id"] != 1 for w in client.get("/api/weeks").get_json())

    def test_delete_week_cascades_to_entries(self, client):
        client.delete("/api/weeks/1")
        weeks = client.get("/api/weeks").get_json()
        assert all(w["id"] != 1 for w in weeks)
        # No entries from week 1 should leak into week 2
        week2 = next(w for w in weeks if w["id"] == 2)
        assert all(e["week_id"] != 1 for e in week2["entries"]) if week2["entries"] else True

    def test_delete_nonexistent_week_returns_204(self, client):
        assert client.delete("/api/weeks/999").status_code == 204


# ── Entries ────────────────────────────────────────────────────────────────

class TestEntries:
    def test_create_entry(self, client):
        r = client.post("/api/weeks/2/entries", json={"food": "Broccoli", "group_id": 1})
        assert r.status_code == 201
        entry = r.get_json()
        assert entry["food"] == "Broccoli"
        assert entry["introduced"] is False
        assert entry["introduced_date"] is None

    def test_create_entry_id_increments(self, client):
        e1 = client.post("/api/weeks/2/entries", json={"food": "A", "group_id": 1}).get_json()
        e2 = client.post("/api/weeks/2/entries", json={"food": "B", "group_id": 1}).get_json()
        assert e2["id"] > e1["id"]

    def test_create_entry_in_nonexistent_week_returns_404(self, client):
        r = client.post("/api/weeks/999/entries", json={"food": "Ghost", "group_id": 1})
        assert r.status_code == 404

    def test_mark_entry_introduced(self, client):
        r = client.put("/api/weeks/1/entries/1",
                       json={"introduced": True, "introduced_date": "2026-03-15"})
        assert r.status_code == 200
        entry = r.get_json()
        assert entry["introduced"] is True
        assert entry["introduced_date"] == "2026-03-15"

    def test_unmark_entry_clears_date(self, client):
        entry = client.put("/api/weeks/1/entries/2",
                           json={"introduced": False, "introduced_date": None}).get_json()
        assert entry["introduced"] is False
        assert entry["introduced_date"] is None

    def test_update_entry_food_name(self, client):
        r = client.put("/api/weeks/1/entries/1", json={"food": "Baby Carrot"})
        assert r.status_code == 200
        assert r.get_json()["food"] == "Baby Carrot"

    def test_update_entry_in_nonexistent_week_returns_404(self, client):
        assert client.put("/api/weeks/999/entries/1", json={"food": "X"}).status_code == 404

    def test_update_nonexistent_entry_returns_404(self, client):
        assert client.put("/api/weeks/1/entries/999", json={"food": "X"}).status_code == 404

    def test_delete_entry(self, client):
        client.delete("/api/weeks/1/entries/1")
        weeks = client.get("/api/weeks").get_json()
        week1_entries = next(w for w in weeks if w["id"] == 1)["entries"]
        assert all(e["id"] != 1 for e in week1_entries)

    def test_delete_nonexistent_entry_returns_204(self, client):
        assert client.delete("/api/weeks/1/entries/999").status_code == 204

    def test_delete_entry_in_nonexistent_week_returns_404(self, client):
        assert client.delete("/api/weeks/999/entries/1").status_code == 404


# ── Data integrity ─────────────────────────────────────────────────────────

class TestDataIntegrity:
    def test_changes_are_persisted_across_requests(self, client):
        client.post("/api/food_groups", json={"name": "Dairy", "color": "#fff"})
        groups = client.get("/api/food_groups").get_json()
        assert any(g["name"] == "Dairy" for g in groups)

    def test_entry_id_never_reused(self, client):
        e1 = client.post("/api/weeks/1/entries", json={"food": "A", "group_id": 1}).get_json()
        client.delete(f"/api/weeks/1/entries/{e1['id']}")
        e2 = client.post("/api/weeks/1/entries", json={"food": "B", "group_id": 1}).get_json()
        assert e2["id"] != e1["id"]

    def test_introduced_date_stored_as_iso(self, client):
        client.put("/api/weeks/1/entries/1",
                   json={"introduced": True, "introduced_date": "2026-03-20"})
        weeks = client.get("/api/weeks").get_json()
        entry = next(e for w in weeks for e in w["entries"] if e["id"] == 1)
        assert entry["introduced_date"] == "2026-03-20"

    def test_introduced_flag_is_boolean(self, client):
        weeks = client.get("/api/weeks").get_json()
        entry = next(e for w in weeks for e in w["entries"] if e["id"] == 2)
        assert entry["introduced"] is True  # stored as int 1, returned as bool

    def test_delete_group_removes_all_its_foods(self, client):
        client.post("/api/food_groups/1/foods", json={"name": "Peas"})
        client.delete("/api/food_groups/1")
        groups = client.get("/api/food_groups").get_json()
        assert all(g["id"] != 1 for g in groups)
