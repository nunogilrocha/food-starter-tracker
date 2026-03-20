"""
API integration tests for Food Starter Tracker.
Each test gets an isolated in-memory data file so tests never touch data.json.
"""
import json
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import app as app_module
from app import app


# ── Fixtures ──────────────────────────────────────────────────────────────

SEED = {
    "food_groups": [
        {"id": 1, "name": "Vegetables", "color": "#e03131"},
        {"id": 2, "name": "Fruits",     "color": "#9c36b5"},
    ],
    "weeks": [
        {
            "id": 1,
            "label": "Week 1",
            "entries": [
                {"id": 1, "food": "Carrot", "group_id": 1,
                 "introduced": False, "introduced_date": None, "notes": ""},
                {"id": 2, "food": "Apple",  "group_id": 2,
                 "introduced": True,  "introduced_date": "2026-03-01", "notes": "loved it"},
            ]
        },
        {
            "id": 2,
            "label": "Week 2",
            "entries": []
        }
    ],
    "next_entry_id": 3
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Flask test client with an isolated data file seeded with SEED."""
    data_file = tmp_path / "data.json"
    data_file.write_text(json.dumps(SEED))
    monkeypatch.setattr(app_module, "DATA_FILE", str(data_file))
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

    def test_create_group(self, client):
        r = client.post("/api/food_groups",
                        json={"name": "Grains", "color": "#2f9e44"})
        assert r.status_code == 201
        created = r.get_json()
        assert created["name"] == "Grains"
        assert created["id"] == 3          # auto-incremented

        # persisted
        groups = client.get("/api/food_groups").get_json()
        assert len(groups) == 3

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

    def test_update_nonexistent_group_returns_404(self, client):
        r = client.put("/api/food_groups/999", json={"name": "Ghost"})
        assert r.status_code == 404

    def test_delete_group_removes_group(self, client):
        r = client.delete("/api/food_groups/1")
        assert r.status_code == 204
        groups = client.get("/api/food_groups").get_json()
        assert all(g["id"] != 1 for g in groups)

    def test_delete_group_also_removes_its_entries(self, client):
        """Deleting group 1 (Vegetables) must remove Carrot from Week 1."""
        client.delete("/api/food_groups/1")
        weeks = client.get("/api/weeks").get_json()
        week1_entries = weeks[0]["entries"]
        assert all(e["group_id"] != 1 for e in week1_entries)

    def test_delete_nonexistent_group_returns_204(self, client):
        # idempotent — deleting something that doesn't exist is safe
        r = client.delete("/api/food_groups/999")
        assert r.status_code == 204


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

    def test_update_nonexistent_week_returns_404(self, client):
        r = client.put("/api/weeks/999", json={"label": "Ghost"})
        assert r.status_code == 404

    def test_delete_week(self, client):
        r = client.delete("/api/weeks/1")
        assert r.status_code == 204
        weeks = client.get("/api/weeks").get_json()
        assert all(w["id"] != 1 for w in weeks)

    def test_delete_nonexistent_week_returns_204(self, client):
        r = client.delete("/api/weeks/999")
        assert r.status_code == 204


# ── Entries ────────────────────────────────────────────────────────────────

class TestEntries:
    def test_create_entry(self, client):
        r = client.post("/api/weeks/2/entries",
                        json={"food": "Broccoli", "group_id": 1})
        assert r.status_code == 201
        entry = r.get_json()
        assert entry["food"] == "Broccoli"
        assert entry["introduced"] is False
        assert entry["introduced_date"] is None

    def test_create_entry_id_increments(self, client):
        e1 = client.post("/api/weeks/2/entries", json={"food": "A", "group_id": 1}).get_json()
        e2 = client.post("/api/weeks/2/entries", json={"food": "B", "group_id": 1}).get_json()
        assert e2["id"] == e1["id"] + 1

    def test_create_entry_in_nonexistent_week_returns_404(self, client):
        r = client.post("/api/weeks/999/entries",
                        json={"food": "Ghost", "group_id": 1})
        assert r.status_code == 404

    def test_mark_entry_introduced(self, client):
        r = client.put("/api/weeks/1/entries/1",
                       json={"introduced": True, "introduced_date": "2026-03-15"})
        assert r.status_code == 200
        entry = r.get_json()
        assert entry["introduced"] is True
        assert entry["introduced_date"] == "2026-03-15"

    def test_unmark_entry_clears_date(self, client):
        # first mark it
        client.put("/api/weeks/1/entries/2",
                   json={"introduced": False, "introduced_date": None})
        entry = client.put("/api/weeks/1/entries/2",
                           json={"introduced": False, "introduced_date": None}).get_json()
        assert entry["introduced"] is False
        assert entry["introduced_date"] is None

    def test_update_entry_food_name(self, client):
        r = client.put("/api/weeks/1/entries/1", json={"food": "Baby Carrot"})
        assert r.status_code == 200
        assert r.get_json()["food"] == "Baby Carrot"

    def test_update_entry_notes(self, client):
        r = client.put("/api/weeks/1/entries/1", json={"notes": "slight rash"})
        assert r.status_code == 200
        assert r.get_json()["notes"] == "slight rash"

    def test_update_entry_in_nonexistent_week_returns_404(self, client):
        r = client.put("/api/weeks/999/entries/1", json={"food": "X"})
        assert r.status_code == 404

    def test_update_nonexistent_entry_returns_404(self, client):
        r = client.put("/api/weeks/1/entries/999", json={"food": "X"})
        assert r.status_code == 404

    def test_delete_entry(self, client):
        r = client.delete("/api/weeks/1/entries/1")
        assert r.status_code == 204
        weeks = client.get("/api/weeks").get_json()
        week1_entries = weeks[0]["entries"]
        assert all(e["id"] != 1 for e in week1_entries)

    def test_delete_nonexistent_entry_returns_204(self, client):
        r = client.delete("/api/weeks/1/entries/999")
        assert r.status_code == 204

    def test_delete_entry_in_nonexistent_week_returns_404(self, client):
        # The parent week doesn't exist — 404 is the correct response
        r = client.delete("/api/weeks/999/entries/1")
        assert r.status_code == 404


# ── Data integrity ─────────────────────────────────────────────────────────

class TestDataIntegrity:
    def test_changes_are_persisted_across_requests(self, client):
        client.post("/api/food_groups", json={"name": "Dairy", "color": "#fff"})
        groups = client.get("/api/food_groups").get_json()
        assert any(g["name"] == "Dairy" for g in groups)

    def test_next_entry_id_never_reused(self, client):
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
