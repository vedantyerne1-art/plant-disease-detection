from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, session

from database.db import get_connection


plants_api = Blueprint("plants_api", __name__)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def current_user_id():
    return session.get("user_id")


@plants_api.get("/api/plants")
def list_plants():
    user_id = current_user_id()
    if not user_id:
        return jsonify({"error": "Please log in to view plants."}), 401
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM plants WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    return jsonify({"plants": [dict(row) for row in rows]})


@plants_api.post("/api/plants")
def create_plant():
    user_id = current_user_id()
    if not user_id:
        return jsonify({"error": "Please log in to add a plant."}), 401
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    plant_type = str(data.get("plant_type", "")).strip()
    planting_date = str(data.get("planting_date", "")).strip() or None
    location = str(data.get("location", "")).strip()
    notes = str(data.get("notes", "")).strip()

    if not name or len(name) > 100:
        return jsonify({"error": "Enter a plant name between 1 and 100 characters."}), 400
    if not plant_type or len(plant_type) > 100:
        return jsonify({"error": "Enter a plant type."}), 400

    now = utc_now()
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO plants (user_id, name, plant_type, planting_date, location, notes, photo_path, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?)",
            (user_id, name, plant_type, planting_date, location[:150], notes[:1000], now, now),
        )
        plant_id = cursor.lastrowid
        plant = connection.execute("SELECT * FROM plants WHERE id = ?", (plant_id,)).fetchone()
    return jsonify({"plant": dict(plant)}), 201


@plants_api.delete("/api/plants/<int:plant_id>")
def delete_plant(plant_id):
    user_id = current_user_id()
    if not user_id:
        return jsonify({"error": "Please log in."}), 401
    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM plants WHERE id = ? AND user_id = ?",
            (plant_id, user_id),
        )
    if cursor.rowcount == 0:
        return jsonify({"error": "Plant not found."}), 404
    return jsonify({"ok": True})
